# [v] update according to new sample
# [] update to langchain
# [] update to ollama cloud


import argparse
from pathlib import Path

from src.extraction.extract_text import extract_text_from_pdf
from src.llm.summary import generate_lab_summary
from src.parsing.parser import parse_lab_report
from src.preprocessing.cleaner import clean_extracted_text
from src.utils.index import save_json, save_text, md_to_pdf


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted_text = extract_text_from_pdf(args.pdf)
    cleaned_text = clean_extracted_text(extracted_text)
    parsed_report = parse_lab_report(cleaned_text)
    llm_summary = generate_lab_summary(parsed_report, model=args.model)

    final_report = {
        "patient": parsed_report["patient"],
        "test_results": parsed_report["test_results"],
        "ai_explanation": llm_summary["ai_explanation"],
        "suggested_steps": llm_summary["suggested_steps"],
        "impressions": parsed_report.get("impressions", []),
        "llm_status": llm_summary["llm_status"],
    }

    save_text(extracted_text, str(output_dir / "extracted.txt"))
    save_text(cleaned_text, str(output_dir / "cleaned.txt"))
    save_json(final_report, str(output_dir / "summary.json"))
    markdown_path = output_dir / "summary.md"
    pdf_path = output_dir / "summary.pdf"

    save_text(render_markdown_report(final_report), str(markdown_path))
    md_to_pdf(markdown_path, pdf_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an AI-assisted summary from a lab report PDF.")
    parser.add_argument("--pdf", default="data/healthreport.pdf", help="Path to the lab report PDF.")
    parser.add_argument("--out", default="outputs", help="Directory where output artifacts are written.")
    parser.add_argument("--model", default="gemma4:latest", help="Ollama model name.")
    return parser.parse_args()


def render_markdown_report(report: dict) -> str:
    patient = report.get("patient", {})
    test_results = report.get("test_results", [])
    ai_explanation = report.get("ai_explanation", [])
    suggested_steps = report.get("suggested_steps", [])

    patient_lines = [
        f"- Patient Name: {patient.get('name') or 'Unknown'}",
        f"- Age: {patient.get('age') or 'Unknown'}",
        f"- Gender: {patient.get('gender') or 'Unknown'}",
        f"- Patient ID: {patient.get('patient_id') or 'Not available'}",
        f"- Date: {patient.get('report_date') or 'Unknown'}",
    ]

    test_lines = []
    for result in test_results:
        label = result["test_name"].title()
        line = f"- {label}: {result['value']}"
        if result.get("unit"):
            line += f" {result['unit']}"
        if result.get("status"):
            line += f" ({result['status']})"
        if result.get("reference_range"):
            line += f" | Range: {result['reference_range']}"
        test_lines.append(line)

    if not test_lines:
        test_lines.append("- No abnormal or notable test results were parsed.")

    explanation_lines = [f"- {item}" for item in ai_explanation] or ["- No AI explanation available."]
    next_step_lines = [f"- {item}" for item in suggested_steps] or ["- No suggested next steps available."]

    return "\n".join(
        [
            "# Lab Report AI Explanation",
            "",
            "## Lab Report Summary",
            *patient_lines,
            "",
            "## Test Results",
            *test_lines,
            "",
            "## AI Explanation",
            *explanation_lines,
            "",
            "## Suggested Next Steps",
            *next_step_lines,
        ]
    )


if __name__ == "__main__":
    main()
