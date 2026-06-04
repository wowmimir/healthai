import asyncio
import markdown
from playwright.async_api import async_playwright

# =========================
# FILES
# =========================

INPUT_MD = "outputs/summary.md"  # Change this to your input file path
OUTPUT_HTML = "outputs/report.html"
OUTPUT_PDF = "outputs/report.pdf"

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
# FULL HTML (English version with standard fonts)
# =========================

full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">

<style>

body {{
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    margin: 40px;
    line-height: 1.6;
    color: #222;
    font-size: 14px;
}}

h1 {{
    border-bottom: 2px solid #2c3e50;
    padding-bottom: 10px;
    color: #2c3e50;
    font-size: 24px;
}}

h2 {{
    margin-top: 30px;
    border-bottom: 1px solid #ccc;
    padding-bottom: 5px;
    color: #34495e;
    font-size: 20px;
}}

h3 {{
    color: #555;
    font-size: 18px;
    margin-top: 20px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    margin-bottom: 20px;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}}

th {{
    background-color: #f5f5f5;
    font-weight: bold;
}}

tr:nth-child(even) {{
    background-color: #f9f9f9;
}}

code {{
    background: #f4f4f4;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
}}

pre {{
    background: #f4f4f4;
    padding: 10px;
    overflow-x: auto;
    border-radius: 5px;
}}

blockquote {{
    border-left: 4px solid #ccc;
    margin: 20px 0;
    padding-left: 20px;
    color: #666;
}}

ul, ol {{
    margin: 10px 0;
    padding-left: 25px;
}}

hr {{
    border: none;
    border-top: 1px solid #eee;
    margin: 20px 0;
}}

.status-out-of-range {{
    color: #e74c3c;
    font-weight: bold;
}}

.status-borderline {{
    color: #f39c12;
    font-weight: bold;
}}

.status-good {{
    color: #27ae60;
    font-weight: bold;
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

import os
os.makedirs("outputs", exist_ok=True)

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"HTML generated: {OUTPUT_HTML}")

# =========================
# HTML -> PDF USING CHROME
# =========================

async def generate_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Convert to absolute path for file:// URL
        abs_path = os.path.abspath(OUTPUT_HTML)
        await page.goto(
            f"file://{abs_path}",
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

print(f"PDF generated successfully: {OUTPUT_PDF}")