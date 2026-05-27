import re
from collections import Counter
from typing import Any


SECTION_HEADINGS = {
    "HEALTH REPORT",
    "LAB REPORT SUMMARY",
    "LAB PARAMETERS NEEDING ATTENTION",
    "LAB PANEL RESULTS",
    "PAST MEDICAL HISTORY",
    "PERSONAL HISTORY",
    "PHYSICAL ACTIVITY",
    "PURPOSE OF VISIT",
    "ROUTINE HEALTH CHECK",
    "PHYSICAL EXAMINATION",
    "VITALS",
    "PHYSICAL EXAM",
    "CARDIOVASCULAR SYSTEM",
    "RESPIRATORY SYSTEM",
    "RADIOLOGY TEST",
    "IMPRESSIONS",
    "APOLLO'S ARTIFICIAL INTELLIGENCE ENABLED RISK SCORES",
}

VALUE_WORDS = {"NEGATIVE", "NORMAL", "CLEAR", "ABSENT", "NIL", "PALE YELLOW"}


def parse_lab_report(cleaned_text: str) -> dict[str, Any]:
    patient = _parse_patient_info(cleaned_text)
    measurements = _parse_measurements(cleaned_text)
    attention_names = _parse_attention_names(cleaned_text)
    impressions = _parse_impressions(cleaned_text)

    selected_results = _select_key_results(measurements, attention_names)

    return {
        "patient": patient,
        "test_results": selected_results,
        "impressions": impressions,
        "raw_measurement_count": len(measurements),
    }


def _parse_patient_info(text: str) -> dict[str, Any]:
    age = None
    gender = None
    patient_name = None
    patient_id = None

    age_gender_match = re.search(r"Age/Gender \(Your age/gender\)\s*:\s*(\d+)\s*Y\s*/\s*([A-Za-z]+)", text, re.IGNORECASE)
    if age_gender_match:
        age = int(age_gender_match.group(1))
        gender = age_gender_match.group(2).capitalize()

    explicit_name = re.search(r"Patient Name \(Your name\)\s*\n\s*([A-Z][A-Z .]+)", text)
    if explicit_name:
        patient_name = _normalize_name(explicit_name.group(1))
    else:
        greeting_name = re.search(r"Dear\s+([A-Z][A-Z .]+)\s+\(Your name\)", text)
        if greeting_name:
            patient_name = _normalize_name(greeting_name.group(1))

    patient_id_match = re.search(r"(?:Patient ID|UHID|ID)\s*:\s*([A-Za-z0-9-]+)", text, re.IGNORECASE)
    if patient_id_match:
        patient_id = patient_id_match.group(1).strip()

    report_date = _parse_report_date(text)

    return {
        "name": patient_name,
        "age": age,
        "gender": gender,
        "patient_id": patient_id,
        "report_date": report_date,
    }


def _parse_report_date(text: str) -> str | None:
    collected_dates = re.findall(r"Sample Collected on\s*:?\s*(\d{2}-\d{2}-\d{4})", text)
    if collected_dates:
        most_common = Counter(collected_dates).most_common(1)[0][0]
        day, month, year = most_common.split("-")
        return f"{year}-{month}-{day}"

    inline_date = re.search(r"Date\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text, re.IGNORECASE)
    if inline_date:
        parts = re.split(r"[/-]", inline_date.group(1))
        day, month, year = parts
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return None


def _normalize_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split())


def _parse_measurements(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results: list[dict[str, Any]] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not _is_test_name_candidate(line):
            i += 1
            continue

        name_parts = [line]
        j = i + 1
        while j < len(lines) and _can_extend_name(name_parts, lines[j]):
            name_parts.append(lines[j])
            j += 1

        if j >= len(lines) or not _is_value(lines[j]):
            i += 1
            continue

        test_name = " ".join(name_parts)
        value = lines[j]
        reference_range = None
        unit = None
        status = "unknown"

        if j + 1 < len(lines) and _is_reference_range(lines[j + 1]):
            reference_range = lines[j + 1]
            unit = _extract_unit(reference_range)
            status = _classify_numeric_result(value, reference_range)
        elif value.upper() in VALUE_WORDS:
            status = "normal"

        results.append(
            {
                "test_name": _normalize_test_name(test_name),
                "value": value,
                "unit": unit,
                "reference_range": reference_range,
                "status": status,
            }
        )
        i = j + 1
        continue

    return _dedupe_measurements(results)


def _parse_attention_names(text: str) -> set[str]:
    match = re.search(
        r"Lab Parameters Needing Attention\s*(.*?)\s*Lab Panel Results",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return set()

    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    names: set[str] = set()

    for line in lines:
        if line.startswith("Description:") or _is_reference_range(line) or _is_value(line):
            continue
        if _is_test_name_candidate(line):
            names.add(_normalize_test_name(line))

    return names


def _parse_impressions(text: str) -> list[str]:
    match = re.search(
        r"Impressions\s*(.*?)\s*Apollo's Artificial Intelligence Enabled Risk Scores",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    impressions: list[str] = []
    for line in match.group(1).splitlines():
        cleaned = line.strip()
        if not cleaned or _is_axis_like_fragment(cleaned) or cleaned.upper() in SECTION_HEADINGS:
            continue
        impressions.append(cleaned.title())
    return impressions


def _select_key_results(measurements: list[dict[str, Any]], attention_names: set[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    use_attention_names = bool(attention_names)

    for measurement in measurements:
        name = measurement["test_name"]
        if use_attention_names:
            is_abnormal = name in attention_names
        else:
            is_abnormal = measurement["status"] in {"low", "high"}
        if not is_abnormal or name in seen:
            continue
        if measurement["status"] == "unknown" and name in attention_names:
            measurement = {**measurement, "status": "attention"}
        selected.append(measurement)
        seen.add(name)

    return selected


def _is_test_name_candidate(line: str) -> bool:
    upper_ratio = sum(1 for char in line if char.isupper()) / max(1, sum(1 for char in line if char.isalpha()))
    if line.upper() in SECTION_HEADINGS:
        return False
    if line.startswith("Description:") or line.startswith("Sample Collected on"):
        return False
    if len(line) < 2 or len(line) > 80:
        return False
    if re.search(r"Your Score|Acceptable Score|Info:|Note:|DISCLAIMER", line, re.IGNORECASE):
        return False
    if upper_ratio < 0.55:
        return False
    if _is_reference_range(line) or _is_value(line):
        return False
    return True


def _can_extend_name(current_parts: list[str], line: str) -> bool:
    if len(current_parts) >= 3:
        return False
    if not _is_test_name_candidate(line):
        return False
    if line.upper() in SECTION_HEADINGS:
        return False
    return True


def _is_value(line: str) -> bool:
    if line.upper() in VALUE_WORDS:
        return True
    return bool(re.fullmatch(r"[0-9][0-9,./-]*", line))


def _is_reference_range(line: str) -> bool:
    return bool(re.search(r"\d+\s*-\s*\d+", line))


def _extract_unit(reference_range: str | None) -> str | None:
    if not reference_range:
        return None
    match = re.search(r"([A-Za-z/%]+(?:/[A-Za-z.]+)?)\s*$", reference_range)
    if match:
        return match.group(1)
    return None


def _classify_numeric_result(value: str, reference_range: str) -> str:
    value_number = _to_float(value)
    if value_number is None:
        return "unknown"

    bounds = re.search(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", reference_range)
    if not bounds:
        return "unknown"

    lower = float(bounds.group(1))
    upper = float(bounds.group(2))

    if value_number < lower:
        return "low"
    if value_number > upper:
        return "high"
    if value_number == lower or value_number == upper:
        return "borderline"
    return "normal"


def _to_float(value: str) -> float | None:
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_test_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    return name.upper()


def _dedupe_measurements(measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for measurement in measurements:
        name = measurement["test_name"]
        current = deduped.get(name)
        if current is None:
            deduped[name] = measurement
            continue
        current_has_range = current.get("reference_range") is not None
        new_has_range = measurement.get("reference_range") is not None
        if not current_has_range and new_has_range:
            deduped[name] = measurement
    return list(deduped.values())


def _is_axis_like_fragment(line: str) -> bool:
    return bool(re.fullmatch(r"[0-9. ]{3,}", line))
