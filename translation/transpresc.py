import json
import os
import re
import requests

from google.cloud import translate_v2 as translate


# =========================================================
# CONFIG
# =========================================================

INPUT_JSON = "outputs/prescription.json"
OUTPUT_MD = "outputs/prescription_translated.md"
GOOGLE_CREDS = "keys/healthai-key.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:31b-cloud"


# =========================================================
# GOOGLE TRANSLATE
# =========================================================

translate_client = translate.Client.from_service_account_json(GOOGLE_CREDS)


# =========================================================
# STATIC MAPS
# =========================================================

SEX_MAP = {
    "Male": "পুরুষ",
    "Female": "মহিলা"
}

FOOD_RELATION_MAP = {
    "after food": "খাবারের পরে",
    "before food": "খাবারের আগে",
    "before breakfast": "সকালের নাস্তার আগে",
    "empty stomach": "খালি পেটে",
    "Not specified": "উল্লেখ করা হয়নি"
}

DOSAGE_MAP = {
    "1 tablet once daily": "প্রতিদিন ১ বার ১টি ট্যাবলেট",
    "1 tablet twice daily": "প্রতিদিন ২ বার ১টি ট্যাবলেট",
    "1 tablet 3 times daily": "প্রতিদিন ৩ বার ১টি ট্যাবলেট",
    "1 tablet three times daily": "প্রতিদিন ৩ বার ১টি ট্যাবলেট",
}


def translate_text(text: str):
    if not text.strip():
        return ""
    result = translate_client.translate(text, target_language="bn")
    return result["translatedText"]


# =========================================================
# OLLAMA REFINEMENT
# =========================================================

def refine_with_ollama(prompt: str):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code != 200:
        print("\nOLLAMA ERROR:")
        print(response.text)
        raise Exception(f"Ollama failed: {response.status_code}")
    
    result = response.json()
    return result["response"].strip()


# =========================================================
# NUMBER SAFETY (Supports Bengali & Western Digits)
# =========================================================

def extract_numbers(text):
    # Matches both standard digits (0-9) and Bengali digits (০-৯)
    return re.findall(r'[\d০-৯]+(?:\.[\d০-৯]+)?', text)


def validate_numbers(original, final):
    # Convert Bengali digits to english digits just for validation parity
    bn_to_en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    
    original_nums = [n.translate(bn_to_en) for n in extract_numbers(original)]
    final_nums = [n.translate(bn_to_en) for n in extract_numbers(final)]
    
    missing = []
    for num in original_nums:
        if num not in final_nums:
            missing.append(num)
    return list(set(missing))


# =========================================================
# BUILD MARKDOWN
# =========================================================

def build_bengali_markdown(data):
    markdown = []

    # HEADER
    markdown.append("# 📋 রোগীর যত্ন পরিকল্পনা এবং ওষুধের নির্দেশিকা\n")
    markdown.append(
        "অনুগ্রহ করে নিচের নির্দেশাবলী মনোযোগ সহকারে মেনে চলুন। "
        "চিকিৎসকের পরামর্শ ছাড়া কোনো ওষুধ বন্ধ বা পরিবর্তন করবেন না।\n"
    )

    # SIMPLE SUMMARY
    markdown.append("## 🌟 সহজ কথায় আপনার করণীয়\n")
    summary_prompt = f"""
You are a Bengali medical assistant.
Write a short patient-friendly Bengali summary.

RULES:
- Preserve medicine names EXACTLY
- Preserve durations EXACTLY
- Preserve dosage counts EXACTLY
- Use simple Bengali
- No markdown
- No hallucinations
- Short paragraph only

DATA:
{json.dumps(data, ensure_ascii=False, indent=2)}
"""
    simple_summary = refine_with_ollama(summary_prompt)
    markdown.append(simple_summary)
    markdown.append("\n---\n")

    # MEDICATION SECTION (Formatted as a Table as seen in your target output)
    markdown.append("## 💊 ওষুধের সময়সূচী")
    
    medications = data.get("medications", [])
    if medications:
        markdown.append("| ওষুধের নাম | খাওয়ার নিয়ম | কখন খাবেন | কতদিন |")
        markdown.append("| :--- | :--- | :--- | :--- |")
        
        for med in medications:
            dosage = DOSAGE_MAP.get(
                med.get("dosage_amount", ""), 
                med.get("dosage_amount", "")
            )
            food_relation = FOOD_RELATION_MAP.get(
                med.get("food_relation", ""), 
                med.get("food_relation", "")
            )
            duration = translate_text(med.get("duration_days", ""))
            name = med.get('name', '')
            
            markdown.append(f"| **{name}** | {dosage} | {food_relation} | {duration} |")
    else:
        markdown.append("\n- কোনো ওষুধের তথ্য পাওয়া যায়নি")
        
    markdown.append("\n---\n")

    # DIETARY
    markdown.append("## 🍏 খাবারের নিয়মকানুন\n")
    dietary = data.get("dietary_advice", [])
    if dietary:
        for advice in dietary:
            translated = translate_text(advice)
            markdown.append(f"- {translated}")
    else:
        markdown.append("- নির্দিষ্ট করা হয়নি")
    markdown.append("\n---\n")

    # TESTS
    markdown.append("## 🧪 নির্ধারিত পরীক্ষা\n")
    tests = data.get("prescribed_tests", [])
    if tests:
        for test in tests:
            markdown.append(f"- {test}")
    else:
        markdown.append("- কোনো পরীক্ষা নির্ধারণ করা হয়নি")
    markdown.append("\n---\n")

    # FOLLOW UP
    markdown.append("## 📆 পরবর্তী সাক্ষাতের তারিখ\n")
    markdown.append(f"**পরবর্তী ভিজিট:** {data.get('follow_up', 'উল্লেখ নেই')}\n")
    markdown.append("---\n")

    # DIAGNOSIS
    diagnosis = data.get("diagnosis", [])
    if diagnosis:
        markdown.append("## 🩺 স্বাস্থ্য পর্যবেক্ষণ\n")
        for item in diagnosis:
            translated = translate_text(item)
            markdown.append(f"- {translated} ({item})")
        markdown.append("")

    # DISCLAIMER
    markdown.append("## ⚠️ সতর্কীকরণ\n")
    markdown.append(
        "এই রিপোর্টটি শুধুমাত্র তথ্যগত সহায়তার জন্য। "
        "চিকিৎসকের সিদ্ধান্ত নেওয়ার আগে অবশ্যই ডাক্তারকে দেখান।"
    )

    return "\n".join(markdown)


# =========================================================
# MAIN
# =========================================================

def main():
    print("\nLoading prescription JSON...\n")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Generating Bengali markdown...\n")
    final_md = build_bengali_markdown(data)

    # NUMBER VALIDATION
    original_text = json.dumps(data, ensure_ascii=False)
    missing_numbers = validate_numbers(original_text, final_md)

    if missing_numbers:
        print("\n⚠️ WARNING: Possible missing numbers in final output:")
        for num in missing_numbers:
            print(f"  - {num}")

    # SAVE
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(final_md)

    print(f"\nSaved Bengali markdown:\n{OUTPUT_MD}\n")


if __name__ == "__main__":
    main()