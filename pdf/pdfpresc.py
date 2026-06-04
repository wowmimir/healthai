import asyncio
import markdown
from playwright.async_api import async_playwright

# =========================
# FILES
# =========================

INPUT_MD = "outputs/prescription_translated.md"
OUTPUT_HTML = "outputs/prescription_translated.html"
OUTPUT_PDF = "outputs/prescription_translated.pdf"

# =========================
# READ MARKDOWN
# =========================

with open(INPUT_MD, "r", encoding="utf-8") as f:
    md_text = f.read()

# =========================
# MARKDOWN -> HTML
# =========================

html_body = markdown.markdown(
    md_text,
    extensions=[
        "tables",
        "fenced_code",
        "nl2br"
    ]
)

# =========================
# FULL HTML
# =========================

full_html = f"""
<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">

<style>

@font-face {{
    font-family: 'Noto Bengali';
    src: url('fonts/NotoSansBengali-Regular.ttf') format('truetype');
}}

body {{
    font-family: 'Noto Bengali', sans-serif;
    margin: 40px;
    line-height: 1.8;
    color: #222;
    font-size: 14px;
}}

h1 {{
    border-bottom: 2px solid black;
    padding-bottom: 10px;
}}

h2 {{
    margin-top: 30px;
    border-bottom: 1px solid #ccc;
    padding-bottom: 5px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}}

th, td {{
    border: 1px solid #444;
    padding: 10px;
    text-align: left;
}}

th {{
    background-color: #f2f2f2;
}}

code {{
    background: #f4f4f4;
    padding: 2px 5px;
}}

pre {{
    background: #f4f4f4;
    padding: 10px;
    overflow-x: auto;
}}

</style>
</head>

<body>

{html_body}

</body>
</html>
"""

# =========================
# SAVE HTML
# =========================

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(full_html)

print("HTML generated.")

# =========================
# HTML -> PDF USING CHROME
# =========================

async def generate_pdf():

    async with async_playwright() as p:

        browser = await p.chromium.launch()

        page = await browser.new_page()

        await page.goto(
            f"file:///{OUTPUT_HTML}",
            wait_until="networkidle"
        )

        await page.pdf(
            path=OUTPUT_PDF,
            format="A4",
            print_background=True,
            margin={
                "top": "20mm",
                "bottom": "20mm",
                "left": "15mm",
                "right": "15mm"
            }
        )

        await browser.close()

asyncio.run(generate_pdf())

print("PDF generated successfully.")