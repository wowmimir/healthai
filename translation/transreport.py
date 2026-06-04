"""
Bengali Translation Script for Health Report
Reads final.json, generates report_bengali.md with faithful translation
Follows pattern from report_translated.md: English digits in tables, Bengali digits in narrative
"""

import json
import re
import requests
from pathlib import Path
from datetime import datetime

# =========================================================
# CONFIGURATION
# =========================================================

INPUT_JSON = "outputs/final.json"
OUTPUT_MD = "outputs/report_translated.md"

GOOGLE_CREDS = "keys/healthai-key.json"  # Update with your path

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:31b-cloud"

# =========================================================
# STATIC MEDICAL TERMS DICTIONARY (Extended)
# =========================================================

MEDICAL_TERMS = {
    # Test names from flagged_tests (10 items)
    "Basophils.": "বেসোফিলস",
    "Vitamin D25 - Hydroxy": "ভিটামিন ডি২৫-হাইড্রক্সি",
    "Triglycerides": "ট্রাইগ্লিসারাইড",
    "V.L.D.L Cholesterol": "ভিএলডিএল কোলেস্টেরল",
    "UIBC": "ইউআইবিসি",
    "Non HDL Cholesterol": "নন-এইচডিএল কোলেস্টেরল",
    "Glycosylated Hemoglobin (HbA1c)": "গ্লাইকোসাইলেটেড হিমোগ্লোবিন (এইচবিএ১সি)",
    "RDW-SD": "আরডিডব্লিউ-এসডি",
    "Gamma Glutamyl Transferase (GGT)": "গামা গ্লুটামাইল ট্রান্সফেরেজ (জিজিটি)",
    "LDL Cholesterol": "এলডিএল কোলেস্টেরল",
    
    # System names (Health Status by Body System table - 12 items)
    "Cardiac Profile": "হৃদযন্ত্র",
    "Blood Disorder": "রক্তের ব্যাধি",
    "Iron": "আয়রন",
    "Vitamin Profile": "ভিটামিন",
    "Infectious Diseases": "সংক্রামক রোগ",
    "Anemia Studies": "রক্তস্বল্পতা",
    "Inflammation": "প্রদাহ",
    "Diabetes Monitoring": "ডায়াবেটিস পর্যবেক্ষণ",
    "Liver Profile": "যকৃত",
    "Kidney Profile": "কিডনি",
    "Electrolytes": "ইলেক্ট্রোলাইট",
    "Thyroid Profile": "থাইরয়েড",
    
    # Status values
    "Out of Range": "স্বাভাবিক সীমার বাইরে",
    "out_of_range": "স্বাভাবিক সীমার বাইরে",
    "OUT_OF_RANGE": "স্বাভাবিক সীমার বাইরে",
    "Borderline": "সীমারেখায়",
    "borderline": "সীমারেখায়",
    "BORDERLINE": "সীমারেখায়",
    "All In Range": "সবকটি স্বাভাবিক",
    "Good": "ভাল",
    "normal": "স্বাভাবিক",
    "high": "বেশি",
    "low": "কম",
    
    # Units
    "mg/dL": "mg/dL",  # Keep as-is (common)
    "ng/mL": "ng/mL",
    "µg/dL": "µg/dL",
    "fl": "fl",
    "U/L": "U/L",
    "%": "%",
    "10^3/µl": "10^3/µl",
    
    # Section headers
    "Patient": "রোগীর তথ্য",
    "Health Score": "স্বাস্থ্য স্কোর",
    "Summary of Key Health Indicators": "মূল স্বাস্থ্য সূচকের সারাংশ",
    "Tests That Need Attention": "যে পরীক্ষাগুলো মনোযোগ প্রয়োজন",
    "Health Status by Body System": "শরীরের বিভিন্ন সিস্টেমের স্বাস্থ্যের অবস্থা",
    "Personalized Health Advisory": "ব্যক্তিগত স্বাস্থ্য পরামর্শ",
    "AI-Generated Summary": "এআই-উত্পন্ন সারাংশ",
    "Overall Assessment": "সামগ্রিক মূল্যায়ন",
    "Critical Findings": "গুরুত্বপূর্ণ পর্যবেক্ষণ",
    "Positive Findings": "ইতিবাচক দিক",
    "Recommendations": "করণীয় পরামর্শ",
    "About Your Health Score": "আপনার স্বাস্থ্য স্কোর সম্পর্কে",
    
    # Table headers
    "#": "#",
    "Test": "পরীক্ষা",
    "Value": "মান",
    "Status": "অবস্থা",
    "Panel": "প্যানেল",
    "System": "সিস্টেম",
    "Total": "মোট",
    "Out of Range (col)": "সীমার বাইরে",
    
    # Gender
    "Male": "পুরুষ",
    "Female": "মহিলা",
    
    # Advisory system names (exact matches from health_advisory)
    "Diabetes": "ডায়াবেটিস",
    "Cardiac Profile": "হৃদযন্ত্র",
    "Liver Profile": "যকৃত",
    "Vitamins Profile": "ভিটামিন",
    "Vitamin Profile": "ভিটামিন",
    
    # Misc
    "Parameter": "প্যারামিটার",
    "Results": "ফলাফল",
    "Note": "দ্রষ্টব্য",
    
    "Out of Range": "স্বাভাবিক সীমার বাইরে",
    "out_of_range": "স্বাভাবিক সীমার বাইরে",
    "OUT_OF_RANGE": "স্বাভাবিক সীমার বাইরে",
    "OUT OF RANGE": "স্বাভাবিক সীমার বাইरे", 
    "Borderline": "সীমারেখায়",
    "borderline": "সীমারেখায়",
    "BORDERLINE": "সীমারেখায়",
    "All In Range": "সবকটি স্বাভাবিক",
    "Good": "ভাল",
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def to_bengali_digits(text: str) -> str:
    """Convert English digits to Bengali digits (for narrative text only)"""
    bengali_digits = {
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
    }
    # Convert digits, preserve decimal points
    result = []
    for char in str(text):
        if char in bengali_digits:
            result.append(bengali_digits[char])
        else:
            result.append(char)
    return ''.join(result)


def extract_numbers(text: str) -> list:
    """Extract all numbers from text (integers and decimals)"""
    return re.findall(r'\d+(?:\.\d+)?', text)


# =========================================================
# GOOGLE TRANSLATE CLIENT
# =========================================================

try:
    from google.cloud import translate_v2 as translate
    translate_client = translate.Client.from_service_account_json(GOOGLE_CREDS)
    GOOGLE_TRANSLATE_AVAILABLE = True
    print("✅ Google Translate client initialized")
except Exception as e:
    print(f"⚠️ Google Translate not available: {e}")
    print("   Will use Ollama-only translation")
    GOOGLE_TRANSLATE_AVAILABLE = False


# =========================================================
# TRANSLATION FUNCTIONS
# =========================================================

def translate_with_google(text: str, target="bn") -> str:
    """Translate text using Google Translate API"""
    if not GOOGLE_TRANSLATE_AVAILABLE or not text.strip():
        return text
    
    try:
        result = translate_client.translate(
            text,
            target_language=target,
            format_="text"
        )
        return result["translatedText"]
    except Exception as e:
        print(f"   ⚠️ Google Translate failed: {e}")
        return text


def refine_with_ollama(text: str, context: str = "general") -> str:
    """Refine translated text using Ollama for natural Bengali"""
    if not text.strip():
        return text
    
    # For pure numbers or very short text, return as-is
    if re.match(r'^[\d\s\.\-\/]+$', text):
        return text
    
    prompt = f"""You are a Bengali medical translator. Convert the following English text to natural, simple Bengali.

RULES:
- Preserve ALL numbers exactly as they appear
- Preserve ALL units (mg/dL, %, etc.) as-is
- Use simple words a rural patient can understand
- Keep medical meaning accurate
- Do not add, remove, or change any information
- Do not hallucinate
- Return ONLY the translated text, no explanations

CONTEXT: {context}

ENGLISH TEXT:
{text}

BENGALI TRANSLATION:"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 1024,
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        translated = result.get("response", "").strip()
        
        # Clean up any markdown or extra spaces
        translated = re.sub(r'^["\']|["\']$', '', translated)
        
        return translated if translated else text
    except Exception as e:
        print(f"   ⚠️ Ollama refinement failed: {e}")
        return text


def translate_hybrid(text: str, context: str = "general") -> str:
    """Hybrid translation: Google Translate + Ollama refinement"""
    if not text.strip():
        return text
    
    # Check static dictionary first
    if text in MEDICAL_TERMS:
        return MEDICAL_TERMS[text]
    
    # For short numbers/units, return as-is
    if re.match(r'^[\d\s\.\-\/]+$', text) or text in ["#", "|", "---"]:
        return text
    
    # Step 1: Google Translate
    translated = translate_with_google(text)
    
    # Step 2: Ollama refinement for natural flow
    refined = refine_with_ollama(translated, context)
    
    return refined


# =========================================================
# BUILD BENGALI MARKDOWN
# =========================================================

def build_bengali_markdown(data: dict) -> str:
    """Generate pure Bengali markdown from final.json data"""
    lines = []
    
    # =========================================================
    # HEADER
    # =========================================================
    lines.append("# মেডিকেল রিপোর্ট সারসংক্ষেপ\n")
    
    # Patient info
    patient = data.get("patient", {})
    lines.append("## রোগীর তথ্য")
    lines.append(f"- **নাম:** {patient.get('name', 'N/A')}")
    lines.append(f"- **বয়স:** {patient.get('age', 'N/A')}")
    
    gender = MEDICAL_TERMS.get(patient.get("gender", ""), patient.get("gender", "N/A"))
    lines.append(f"- **লিঙ্গ:** {gender}")
    
    patient_id = patient.get("patient_id")
    if patient_id:
        lines.append(f"- **রোগী আইডি:** {patient_id}")
    lines.append("")
    
    # =========================================================
    # HEALTH SCORE
    # =========================================================
    # Health score
    health_score = data.get("health_score", {})
    ai_summary = data.get("ai_summary", {})

    score = health_score.get("score")
    category = health_score.get("category", "")
    category_bn = MEDICAL_TERMS.get(category, category)

    lines.append("## স্বাস্থ্য স্কোর")
    lines.append("")
    if score:
        # Convert score to Bengali digits
        score_bn = to_bengali_digits(str(score))
        lines.append(f"**{score_bn}/১০০** — {category_bn}")
        lines.append("")
    
    # Use health_score_explanation from ai_summary - convert numbers to Bengali digits
    score_explanation = ai_summary.get("health_score_explanation", "")
    if score_explanation:
        translated = translate_hybrid(score_explanation, "health_score")
        # Convert numbers to Bengali digits for narrative text
        translated = to_bengali_digits(translated)
        lines.append(f"> {translated}")
        lines.append("")
    
    # =========================================================
    # KEY INDICATORS
    # =========================================================
    key_indicators = data.get("key_indicators", {})
    lines.append("## মূল স্বাস্থ্য সূচকের সারাংশ")
    lines.append("")
    # Keep English digits for counts (table-style data)
    lines.append(f"- **মোট পরীক্ষিত প্যারামিটার:** {key_indicators.get('total_parameters', 'N/A')}")
    lines.append(f"- **সীমারেখার ফলাফল:** {key_indicators.get('borderline_count', 'N/A')}")
    lines.append(f"- **স্বাভাবিক সীমার বাইরের ফলাফল:** {key_indicators.get('out_of_range_count', 'N/A')}")
    lines.append("")
    
    # =========================================================
    # FLAGGED TESTS TABLE (English digits)
    # =========================================================
    flagged_tests = data.get("flagged_tests", [])
    
    lines.append("## যে পরীক্ষাগুলো মনোযোগ প্রয়োজন")
    lines.append("")
    lines.append("| # | পরীক্ষা | মান | অবস্থা | প্যানেল |")
    lines.append("|---|---------|------|--------|---------|")
    
    for test in flagged_tests[:10]:
        test_name = test.get("test_name", "")
        test_name_bn = MEDICAL_TERMS.get(test_name, test_name)
        
        value = test.get("value", "")
        unit = test.get("unit", "")
        # Keep English digits in table
        value_str = f"{value} {unit}".strip()
        
        status = test.get("status", "")
        status_bn = MEDICAL_TERMS.get(status, MEDICAL_TERMS.get(status.upper(), status))
        
        panel_name = test.get("panel_name", "")
        panel_bn = MEDICAL_TERMS.get(panel_name, panel_name)
        
        lines.append(f"| {test.get('severity_rank', '#')} | {test_name_bn} | {value_str} | {status_bn} | {panel_bn} |")
    
    lines.append("")
    
    # =========================================================
    # SYSTEM SUMMARY TABLE (English digits)
    # =========================================================
    system_summary = data.get("system_summary", [])
    
    lines.append("## শরীরের বিভিন্ন সিস্টেমের স্বাস্থ্যের অবস্থা")
    lines.append("")
    lines.append("| সিস্টেম | মোট | সীমারেখায় | সীমার বাইরে | অবস্থা |")
    lines.append("|---------|-----|-------------|--------------|---------|")
    
    for system in system_summary:
        panel_name = system.get("panel_name", "")
        panel_bn = MEDICAL_TERMS.get(panel_name, panel_name)
        
        # Keep English digits in table
        total = system.get("total", 0)
        borderline = system.get("borderline", 0)
        out_of_range = system.get("out_of_range", 0)
        status = system.get("status", "")
        status_bn = MEDICAL_TERMS.get(status, status)
        
        lines.append(f"| {panel_bn} | {total} | {borderline} | {out_of_range} | {status_bn} |")
    
    lines.append("")
    
    # =========================================================
    # HEALTH ADVISORY (Bengali digits for narrative)
    # =========================================================
    health_advisory = data.get("health_advisory", [])
    
    lines.append("## ব্যক্তিগত স্বাস্থ্য পরামর্শ")
    lines.append("")
    
    for card in health_advisory:
        system_name = card.get("system", "")
        system_bn = MEDICAL_TERMS.get(system_name, system_name)
        
        test_name = card.get("test_name", "")
        test_name_bn = MEDICAL_TERMS.get(test_name, test_name)
        
        value = card.get("value", "")
        unit = card.get("unit", "")
        
        # Fix status lookup
        status_raw = card.get("status", "")
        # Try different variations
        status_bn = MEDICAL_TERMS.get(status_raw)
        if not status_bn:
            status_bn = MEDICAL_TERMS.get(status_raw.replace("_", " ").title())
        if not status_bn:
            status_bn = MEDICAL_TERMS.get(status_raw.upper())
        if not status_bn:
            status_bn = status_raw  # fallback
        
        description = card.get("condition_description", "")
        translated_description = translate_hybrid(description, "advisory")
        translated_description = to_bengali_digits(translated_description)
        
        lines.append(f"### {system_bn}")
        lines.append("")
        lines.append(f"**{test_name_bn}:** {value} {unit} — {status_bn}")
        lines.append("")
        lines.append(translated_description)
        lines.append("")
    
    # =========================================================
    # AI-GENERATED SUMMARY (Bengali digits for narrative)
    # =========================================================
    lines.append("## এআই-উত্পন্ন সারাংশ")
    lines.append("")
    
    # Overall Assessment
    overall = ai_summary.get("overall", "")
    if overall:
        lines.append("### সামগ্রিক মূল্যায়ন")
        lines.append("")
        translated_overall = translate_hybrid(overall, "overall")
        translated_overall = to_bengali_digits(translated_overall)
        lines.append(translated_overall)
        lines.append("")
    
    # Critical Findings
    critical_findings = ai_summary.get("critical_findings", [])
    if critical_findings:
        lines.append("### গুরুত্বপূর্ণ পর্যবেক্ষণ")
        lines.append("")
        for finding in critical_findings:
            translated_finding = translate_hybrid(finding, "finding")
            translated_finding = to_bengali_digits(translated_finding)
            lines.append(f"- {translated_finding}")
        lines.append("")
    
    # Positive Findings
    positive_findings = ai_summary.get("positive_findings", [])
    if positive_findings:
        lines.append("### ইতিবাচক দিক")
        lines.append("")
        for finding in positive_findings:
            translated_finding = translate_hybrid(finding, "finding")
            translated_finding = to_bengali_digits(translated_finding)
            lines.append(f"- {translated_finding}")
        lines.append("")
    
    # Recommendations
    recommendations = ai_summary.get("recommendations", [])
    if recommendations:
        lines.append("### করণীয় পরামর্শ")
        lines.append("")
        for rec in recommendations:
            translated_rec = translate_hybrid(rec, "recommendation")
            translated_rec = to_bengali_digits(translated_rec)
            lines.append(f"- {translated_rec}")
        lines.append("")
    
    # Health Score Explanation (if not already shown above)
    health_score_explanation = ai_summary.get("health_score_explanation", "")
    if health_score_explanation and health_score_explanation != score_explanation:
        lines.append("### আপনার স্বাস্থ্য স্কোর সম্পর্কে")
        lines.append("")
        translated_explanation = translate_hybrid(health_score_explanation, "health_score")
        translated_explanation = to_bengali_digits(translated_explanation)
        lines.append(translated_explanation)
        lines.append("")
    
    # =========================================================
    # FOOTER / DISCLAIMER
    # =========================================================
    lines.append("---")
    lines.append("")
    lines.append("*এই সারাংশ শুধুমাত্র তথ্যগত সহায়তার জন্য একটি এআই সিস্টেম দ্বারা তৈরি। চিকিৎসা পরামর্শ, রোগ নির্ণয় বা চিকিৎসার জন্য দয়া করে একজন যোগ্যতাসম্পন্ন স্বাস্থ্যসেবা পেশাদারের সাথে পরামর্শ করুন।*")
    lines.append("")
    
    return "\n".join(lines)


# =========================================================
# MAIN
# =========================================================

def main():
    print("\n" + "="*60)
    print("   BENGALI HEALTH REPORT TRANSLATOR")
    print("="*60 + "\n")
    
    # Load input JSON
    print(f"📂 Loading: {INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"   Patient: {data.get('patient', {}).get('name', 'Unknown')}")
    print(f"   Health Score: {data.get('health_score', {}).get('score', 'N/A')}/100")
    print(f"   Flagged Tests: {len(data.get('flagged_tests', []))}")
    print(f"   Advisory Cards: {len(data.get('health_advisory', []))}")
    print()
    
    # Generate Bengali markdown
    print("🔄 Generating Bengali markdown...")
    final_md = build_bengali_markdown(data)
    
    # Save output
    output_path = Path(OUTPUT_MD)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md)
    
    print(f"\n✅ Bengali report saved to: {OUTPUT_MD}")
    print(f"   File size: {output_path.stat().st_size:,} bytes")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()