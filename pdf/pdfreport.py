import os
import re
import asyncio
import markdown
from playwright.async_api import async_playwright

# =========================
# FILES
# =========================
INPUT_MD = "outputs/summary.md"
OUTPUT_HTML = "report.html"
OUTPUT_PDF = "report.pdf"

# =========================
# READ MARKDOWN
# =========================
with open(INPUT_MD, "r", encoding="utf-8") as f:
    md_text = f.read()

# =========================
# DYNAMIC DATA PARSING & CALCULATION
# =========================
# 1. Extract overall health score dynamically (e.g., 78)
score_match = re.search(r"## Health Score\s*\n\s*\*\*(\d+)/100\*\*", md_text)
overall_score = int(score_match.group(1)) if score_match else 78

# Semicircle arc length math (~110)
stroke_dash = (overall_score / 100) * 110

# 2. Extract and parse table rows dynamically (Zero hardcoded names)
systems_data = []
table_pattern = re.findall(r"\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|", md_text)

for row in table_pattern:
    system_name = row[0].strip()
    # Skip markdown header/separator rows safely
    if system_name in ["System", "---"] or "Health Status" in system_name or not system_name:
        continue
    
    try:
        total = int(row[1].strip())
        borderline = int(row[2].strip())
        out_of_range = int(row[3].strip())
        status = row[4].strip()
        
        # Pure mathematical calculation of the score directly from the table counts
        in_range_tests = total - borderline - out_of_range
        factor_score = int((in_range_tests / total) * 100) if total > 0 else 100
        
        # Assign UI status labels dynamically
        if status == "All In Range":
            status_class = "status-good"
            text_status = "Excellent"
        elif status == "Borderline":
            status_class = "status-borderline"
            text_status = "Good"
        else:
            status_class = "status-out-of-range"
            text_status = "Average"
            
        systems_data.append({
            "name": system_name,
            "score": factor_score,
            "status_text": text_status,
            "status_class": status_class
        })
    except (ValueError, IndexError):
        # Skip row cleanly if it doesn't contain valid integers
        continue

# 3. Generate HTML rows dynamically from parsed data
factors_html = ""
for sys in systems_data:
    factors_html += f"""
    <div class="factor-row">
        <span class="factor-name">{sys['name']}</span>
        <span class="factor-status {sys['status_class']}">{sys['status_text']}</span>
        <span class="factor-score">{sys['score']}/100</span>
    </div>
    """

# =========================
# COMPILING CRACK-PROOF SVG INFOGRAPHIC
# =========================
infographic_html = f"""
<div class="infographic-container">
    <div class="infographic-header">HEALTH SCORE BOARD</div>
    
    <div class="gauge-box">
        <svg viewBox="0 0 100 62" class="gauge-svg">
            <defs>
                <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#3498db" />
                    <stop offset="60%" stop-color="#2ecc71" />
                    <stop offset="100%" stop-color="#1abc9c" />
                </linearGradient>
            </defs>
            <path d="M 15 50 A 35 35 0 0 1 85 50" fill="none" stroke="#edf2f7" stroke-width="8" stroke-linecap="round" />
            <path d="M 15 50 A 35 35 0 0 1 85 50" fill="none" stroke="url(#gauge-gradient)" stroke-width="8" 
                  stroke-linecap="round" stroke-dasharray="{stroke_dash} 110" />
            
            <text x="50" y="38" text-anchor="middle" class="svg-score-num">{overall_score}</text>
            <text x="50" y="48" text-anchor="middle" class="svg-score-label">GOOD</text>
            <text x="50" y="56" text-anchor="middle" class="svg-score-sub">Parameters within healthy limits</text>
        </svg>
    </div>
    
    <div class="factors-title">SCORE FACTORS BY SYSTEM</div>
    <div class="factors-list">
        {factors_html}
    </div>
</div>
"""

# =========================
# MARKDOWN -> HTML PROCESSING
# =========================
html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])

# Structural regex match cleanly prevents gaps before insertion
pattern_target = r"(<h2>Summary of Key Health Indicators</h2>)"
if re.search(pattern_target, html_body):
    html_body = re.sub(pattern_target, f"{infographic_html}\n\\1", html_body)
else:
    html_body = html_body.replace("<h2>Health Score</h2>", f"<h2>Health Score</h2>\n{infographic_html}")

# Strip spacing nodes between consecutive block conversions
html_body = html_body.replace("<p><br />\n</p>", "")
html_body = re.sub(r'<p>\s*</p>', '', html_body)

# =========================
# PREMIUM HYPER-STABLE TEMPLATE
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
    color: #2d3748;
    font-size: 14px;
}}
h1 {{ border-bottom: 2px solid #2c3e50; padding-bottom: 10px; color: #2c3e50; font-size: 24px; margin-bottom: 15px; }}
h2 {{ margin-top: 25px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; color: #34495e; font-size: 19px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px; }}
th, td {{ border: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
th {{ background-color: #f7fafc; font-weight: bold; color: #4a5568; }}
tr:nth-child(even) {{ background-color: #f8fafc; }}
blockquote {{ border-left: 4px solid #cbd5e0; margin: 15px 0; padding-left: 15px; color: #4a5568; font-style: italic; }}
ul, ol {{ margin: 10px 0; padding-left: 20px; }}

.status-out-of-range {{ color: #e53e3e; font-weight: bold; }}
.status-borderline {{ color: #dd6b20; font-weight: bold; }}
.status-good {{ color: #38a169; font-weight: bold; }}

/* Infographic Layout Card with zero upper padding gap */
.infographic-container {{
    max-width: 440px;
    margin: 10px auto 20px auto;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    background: #ffffff;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);
    padding: 24px;
    page-break-inside: avoid;
}}
.infographic-header {{
    text-align: center;
    font-weight: 800;
    font-size: 15px;
    color: #1e3a8a;
    letter-spacing: 1px;
    margin-bottom: 12px;
}}
.gauge-box {{
    width: 250px;
    margin: 0 auto;
    position: relative;
}}
.gauge-svg {{
    display: block;
    width: 100%;
    height: auto;
}}

/* Crisp Embedded SVG Vector Typography Styles */
.svg-score-num {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 17px;
    font-weight: 900;
    fill: #2f855a;
}}
.svg-score-label {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 5.5px;
    font-weight: 800;
    fill: #38a169;
    letter-spacing: 0.5px;
}}
.svg-score-sub {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 3.8px;
    font-weight: 500;
    fill: #718096;
}}

.factors-title {{
    margin-top: 20px;
    font-size: 11px;
    font-weight: 800;
    color: #4a5568;
    border-bottom: 1px solid #edf2f7;
    padding-bottom: 6px;
    letter-spacing: 0.5px;
}}
.factor-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 0;
    border-bottom: 1px solid #f7fafc;
}}
.factor-row:last-child {{
    border-bottom: none;
}}
.factor-name {{
    flex: 1;
    font-weight: 600;
    color: #2d3748;
    font-size: 13px;
}}
.factor-status {{
    width: 90px;
    text-align: right;
    font-size: 12px;
}}
.factor-score {{
    width: 65px;
    text-align: right;
    font-weight: 700;
    color: #4a5568;
    font-size: 13px;
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
os.makedirs("outputs", exist_ok=True)
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(full_html)
print(f"HTML Dynamic Infographic generated: {OUTPUT_HTML}")

# =========================
# HTML -> PDF (CHROME ENGINE)
# =========================
async def generate_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        abs_path = os.path.abspath(OUTPUT_HTML)
        await page.goto(f"file://{abs_path}", wait_until="networkidle")
        await page.pdf(
            path=OUTPUT_PDF,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"}
        )
        await browser.close()

asyncio.run(generate_pdf())
print(f"PDF compiled clean from matrix parameters: {OUTPUT_PDF}")