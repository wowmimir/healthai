import json
from typing import Any
from urllib import error, request


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def generate_lab_summary(parsed_report: dict[str, Any], model: str = "gemma4:latest") -> dict[str, Any]:
    prompt = _build_prompt(parsed_report)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "ai_explanation": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "suggested_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["ai_explanation", "suggested_steps"],
        },
    }

    try:
        response = _post_json(OLLAMA_URL, payload)
        model_response = json.loads(response["response"])
        return {
            "ai_explanation": _clean_bullets(model_response.get("ai_explanation", [])),
            "suggested_steps": _clean_bullets(model_response.get("suggested_steps", [])),
            "llm_status": "ok",
        }
    except (error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return _fallback_summary(parsed_report)


def _build_prompt(parsed_report: dict[str, Any]) -> str:
    safe_payload = {
        "patient": parsed_report.get("patient", {}),
        "test_results": parsed_report.get("test_results", []),
        "impressions": parsed_report.get("impressions", []),
    }
    payload_json = json.dumps(safe_payload, indent=2, ensure_ascii=False)

    return (
        "You are generating a concise lab report explanation for a patient-facing summary.\n"
        "Use only the provided structured data.\n"
        "Do not invent patient demographics, diagnosis, values, ranges, or medications.\n"
        "Keep explanations short, factual, and easy to understand.\n"
        "Suggested steps must be conservative and informational, not prescriptive treatment.\n"
        "Always mention follow-up with a clinician for abnormal or unclear findings.\n"
        "Return valid JSON with exactly two keys: ai_explanation and suggested_steps.\n\n"
        f"Structured report:\n{payload_json}"
    )


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _fallback_summary(parsed_report: dict[str, Any]) -> dict[str, Any]:
    test_results = parsed_report.get("test_results", [])
    explanations: list[str] = []
    steps: list[str] = []

    if not test_results:
        explanations.append("No clearly abnormal lab findings were parsed from the report.")
        steps.append("Review the extracted report manually and confirm the PDF text was parsed correctly.")
    else:
        for result in test_results[:6]:
            status = result.get("status", "attention")
            name = result.get("test_name", "UNKNOWN TEST").replace("_", " ").title()
            value = result.get("value")
            reference = result.get("reference_range")
            if reference:
                explanations.append(f"{name} is {status} at {value} compared with the stated range {reference}.")
            else:
                explanations.append(f"{name} needs attention with a reported value of {value}.")

        steps.extend(
            [
                "Discuss these findings with a clinician, especially the abnormal results.",
                "Repeat or confirm any abnormal tests if advised by the treating doctor.",
                "Use the full report and clinical history together rather than acting on this summary alone.",
            ]
        )

    return {
        "ai_explanation": _clean_bullets(explanations),
        "suggested_steps": _clean_bullets(steps),
        "llm_status": "fallback",
    }


def _clean_bullets(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        if not item:
            continue
        text = " ".join(item.split())
        if text:
            cleaned.append(text)
    return cleaned
