import re
from typing import Iterable


BOILERPLATE_PATTERNS = (
    r"Apollo Clinic",
    r"#1, Near Mc\.Donalds, Prakasam Salai, Valasaravakkam, Chennai, Tamil Nadu, India - 600087",
    r"Phone No: 1860 500 7788",
    r"email: kothandaram\.rj@apolloclinic\.com",
    r"Disclaimer:All lab results are subject to clinical interpretation by qualified medical professionals and the report is not subject to use for any medicolegal purpose",
)

DROP_LINE_PATTERNS = (
    r"^Lab Reports$",
    r"^Your lab reports are available\..*",
    r"^x-ray chest pa$",
    r"^sono mamography - screening$",
    r"^ultrasound screening whole a.*$",
    r"^ecg$",
    r"^complete blood count \(cbc\), gl.*$",
)


def clean_extracted_text(text: str) -> str:
    normalized = _normalize_text(text)
    pages = [_clean_page(page) for page in _split_pages(normalized)]
    pages = [page for page in pages if page.strip()]
    return "\n\n".join(pages).strip()


def _normalize_text(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "Â ": " ",
        "Â": "",
        "â€™": "'",
        "â€¦": "...",
        "â€“": "-",
        "â€”": "-",
        "°F": " F",
        "µ": "u",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _split_pages(text: str) -> list[str]:
    pages = re.split(r"\n\s*--- PAGE \d+ ---\s*\n", text)
    return [page.strip() for page in pages if page.strip()]


def _clean_page(page: str) -> str:
    lines = [line.strip() for line in page.splitlines()]
    cleaned_lines: list[str] = []

    for line in lines:
        if not line:
            cleaned_lines.append("")
            continue
        if _is_boilerplate(line) or _should_drop_line(line) or _is_axis_noise(line):
            continue
        cleaned_lines.append(line)

    text = _collapse_blank_lines(cleaned_lines)
    text = re.sub(r"\n:\s*", "\n", text)
    return text.strip()


def _is_boilerplate(line: str) -> bool:
    return any(re.fullmatch(pattern, line) for pattern in BOILERPLATE_PATTERNS)


def _should_drop_line(line: str) -> bool:
    return any(re.fullmatch(pattern, line) for pattern in DROP_LINE_PATTERNS)


def _is_axis_noise(line: str) -> bool:
    if line == "*":
        return True
    if re.fullmatch(r"(mg/dL|pg/mL|ng/mL|g/dL|U/L|mmol/L|fL|pg|%|cells/cu\.mm|Cells/cu\.mm|/hpf|uIU/mL|ug/dL)", line):
        return True
    if re.search(r"[A-Za-z]", line):
        return False
    numeric_fragments = re.findall(r"\d+(?:\.\d+)?", line)
    if len(numeric_fragments) >= 3:
        return True
    if len(numeric_fragments) >= 2 and " " in line and "-" not in line:
        return True
    if re.fullmatch(r"[0-9.]{8,}", line):
        return True
    return False


def _collapse_blank_lines(lines: Iterable[str]) -> str:
    collapsed: list[str] = []
    previous_blank = False

    for line in lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        collapsed.append(line)
        previous_blank = is_blank

    return "\n".join(collapsed)
