import os
import re
import asyncio
import markdown
from playwright.async_api import async_playwright

# =========================
# FILES
# =========================
INPUT_MD = "outputs/report_translated.md"
OUTPUT_HTML = "report_translated.html"
OUTPUT_PDF = "report_translated.pdf"

# =========================
# UTILITY FUNCTIONS FOR NUMBER CONVERSION
# =========================
BENGALI_DIGITS = "০১২৩৪৫৬৭৮৯"
ENGLISH_DIGITS = "0123456789"

bn_to_en_table = str.maketrans(BENGALI_DIGITS, ENGLISH_DIGITS)
en_to_bn_table = str.maketrans(ENGLISH_DIGITS, BENGALI_DIGITS)

def bn_to_en(text):
    return text.translate(bn_to_en_table)

def en_to_bn(text):
    return str(text).translate(en_to_bn_table)

# =========================
# READ MARKDOWN
# =========================
with open(INPUT_MD, "r", encoding="utf-8") as f:
    md_text = f.read()

# =========================
# DYNAMIC DATA PARSING & CALCULATION
# =========================
# ১. স্বাস্থ্য স্কোর এক্সট্রাকশন (যেমন: ৭৮)
score_match = re.search(r"## স্বাস্থ্য স্কোর\s*\n\s*\*\*([০-৯]+)/([০-৯]+)\*\*", md_text)
if score_match:
    overall_score_bn = score_match.group(1)
    overall_score_en = int(bn_to_en(overall_score_bn))
else:
    overall_score_en = 78
    overall_score_bn = en_to_bn(78)

# সেমি-সার্কেল আর্কের দৈর্ঘ্য নির্ধারণ (~১১০)
stroke_dash = (overall_score_en / 100) * 110

# ২. বডি সিস্টেম টেবিল ডাইনামিক পার্সিং (সম্পূর্ণ ডাইনামিক)
systems_data = []
table_pattern = re.findall(r"\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|", md_text)

for row in table_pattern:
    system_name = row[0].strip()
    
    # টেবিল হেডার, সেপারেটর এবং অপ্রাসঙ্গিক রো বাদ দেওয়া হচ্ছে
    if system_name in ["System", "---", "পরীক্ষা", "#", "সিস্টেম"] or "অবস্থা" in system_name or not system_name:
        continue
    
    try:
        # বাংলা বা ইংরেজি যেকোনো সংখ্যাকে ডাইনামিক্যালি রিড করে ইংরেজিতে কনভার্ট করা হচ্ছে ক্যালকুলেশনের জন্য
        total_val = int(bn_to_en(row[1].strip()))
        borderline_val = int(bn_to_en(row[2].strip()))
        out_of_range_val = int(bn_to_en(row[3].strip()))
        status = row[4].strip()
        
        # আপনার আসল ফর্মুলা ব্যবহার করে ডাইনামিক স্কোর গণনা
        in_range_tests = total_val - borderline_val - out_of_range_val
        factor_score_en = int((in_range_tests / total_val) * 100) if total_val > 0 else 100
        factor_score_bn = en_to_bn(factor_score_en)
        
        # স্ট্যাটাস লেবেল নির্ধারণ
        if "স্বাভাবিক সীমার বাইরে" in status or "Out of Range" in status:
            status_class = "status-out-of-range"
            text_status = "মাঝামাঝি"
        elif "সীমারেখা" in status or "Borderline" in status:
            status_class = "status-borderline"
            text_status = "ভালো"
        else:
            status_class = "status-good"
            text_status = "অসাধারণ"
            
        systems_data.append({
            "name": system_name,
            "score": factor_score_bn,
            "status_text": text_status,
            "status_class": status_class
        })
    except (ValueError, IndexError):
        # সংখ্যা না থাকলে সেই রোটি এড়িয়ে যাওয়া হবে (যেমন মেইন টেস্ট টেবিলগুলো ফিল্টার হয়ে যাবে)
        continue

# ডাইনামিক রো জেনারেশন
factors_html = ""
for sys in systems_data:
    factors_html += f"""
    <div class="factor-row">
        <span class="factor-name">{sys['name']}</span>
        <span class="factor-status {sys['status_class']}">{sys['status_text']}</span>
        <span class="factor-score">{sys['score']}/১০০</span>
    </div>
    """

# =========================
# COMPILING BENGALI SVG INFOGRAPHIC
# =========================
infographic_html = f"""
<div class="infographic-container">
    <div class="infographic-header">হেলথ স্কোর বোর্ড</div>
    
    <div class="gauge-box">
        <svg viewBox="0 0 100 64" class="gauge-svg">
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
            
            <text x="50" y="35" text-anchor="middle" class="svg-score-num">{overall_score_bn}</text>
            <text x="50" y="43" text-anchor="middle" class="svg-score-base">/১০০</text>
            <text x="50" y="50" text-anchor="middle" class="svg-score-label">ভালো</text>
            <text x="50" y="58" text-anchor="middle" class="svg-score-sub">প্যারামিটার গুলি সীমার মধ্যে রয়েছে</text>
        </svg>
    </div>
    
    <div class="factors-title">বডি সিস্টেম অনুযায়ী স্কোরের কারণ</div>
    <div class="factors-list">
        {factors_html}
    </div>
</div>
"""

# =========================
# MARKDOWN -> HTML PROCESSING
# =========================
html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])

# নিখুঁত পজিশনিং নিশ্চিত করতে টাইটেল টার্গেট করা হচ্ছে
pattern_target = r"(<h2>মূল স্বাস্থ্য সূচকের সারাংশ</h2>)"
if re.search(pattern_target, html_body):
    html_body = re.sub(pattern_target, f"{infographic_html}\n\\1", html_body)
else:
    html_body = html_body.replace("<h2>স্বাস্থ্য স্কোর</h2>", f"<h2>স্বাস্থ্য স্কোর</h2>\n{infographic_html}")

# যেকোনো অনাকাঙ্ক্ষিত ফাঁকা প্যারাগ্রাফ বা ব্রেক ট্যাগ রিমুভ করা হচ্ছে
html_body = html_body.replace("<p><br />\n</p>", "")
html_body = re.sub(r'<p>\s*</p>', '', html_body)

# =========================
# FULL HTML WITH HIGH-QUALITY BENGALI FONTS
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

/* ইনফোগ্রাফিক লেআউট বক্স (কোনো আপার গ্যাপ বা স্পেসিং ত্রুটি নেই) */
.infographic-container {{
    max-width: 440px;
    margin: 10px auto 25px auto;
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
    font-size: 16px;
    color: #1e3a8a;
    letter-spacing: 0.5px;
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

/* সুনির্দিষ্ট ভেক্টর টাইপোগ্রাফি স্টাইল */
.svg-score-num {{
    font-family: 'Noto Bengali', sans-serif;
    font-size: 16px;
    font-weight: 900;
    fill: #2f855a;
}}
.svg-score-base {{
    font-family: 'Noto Bengali', sans-serif;
    font-size: 5px;
    font-weight: 700;
    fill: #718096;
}}
.svg-score-label {{
    font-family: 'Noto Bengali', sans-serif;
    font-size: 5.5px;
    font-weight: 800;
    fill: #38a169;
    letter-spacing: 0.5px;
}}
.svg-score-sub {{
    font-family: 'Noto Bengali', sans-serif;
    font-size: 3.8px;
    font-weight: 500;
    fill: #718096;
}}

.factors-title {{
    margin-top: 20px;
    font-size: 12px;
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
print(f"HTML generated successfully: {OUTPUT_HTML}")

# =========================
# HTML -> PDF USING PLAYWRIGHT
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
print(f"Bengali Health Report PDF generated successfully: {OUTPUT_PDF}")