import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from pathlib import Path


def ensure_parent(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)


def save_text(text: str, output_path: str) -> None:
    path = Path(output_path)
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def save_json(data: Any, output_path: str) -> None:
    path = Path(output_path)
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def md_to_pdf(md_path: str | Path, pdf_path: str | Path | None = None) -> Path:
    md_path = Path(md_path)
    pdf_path = Path(pdf_path) if pdf_path else md_path.with_suffix(".pdf")

    md_text = md_path.read_text(encoding="utf-8")
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    story = []
    in_code_block = False
    code_lines = []

    for line in md_text.splitlines():
        if line.startswith("```"):
            if in_code_block:
                story.append(Preformatted("\n".join(code_lines), styles["Code"]))
                story.append(Spacer(1, 6))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], styles["Heading3"]))
        elif line.strip() == "":
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)
    return pdf_path
