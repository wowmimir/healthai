import fitz
from pathlib import Path


def extract_text_from_pdf(pdf_path:str)->str:

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)

    extracted_pages = []

    for page_num, page in enumerate(doc):
        blocks = page.get_text("blocks")
        ordered_blocks = sorted(blocks, key=lambda block: (round(block[1], 1), round(block[0], 1)))
        text = "\n".join(block[4].strip() for block in ordered_blocks if block[4].strip())

        extracted_pages.append(
            f"\n\n--- PAGE {page_num + 1} ---\n\n{text}"
        )

    doc.close()

    return "\n".join(extracted_pages)
