import json
import re
import requests

from google.cloud import translate_v2 as translate


# =========================================================
# CONFIG
# =========================================================

INPUT_JSON = "outputs/summary.json"
OUTPUT_MD = "outputs/report_translated.md"

GOOGLE_CREDS = "keys/healthai-key.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:31b-cloud"


# =========================================================
# GOOGLE TRANSLATE CLIENT
# =========================================================

translate_client = translate.Client.from_service_account_json(
    GOOGLE_CREDS
)


# =========================================================
# STATIC MAPS
# =========================================================

GENDER_MAP = {
    "Male": "পুরুষ",
    "Female": "মহিলা",
    "Other": "অন্যান্য"
}

STATUS_MAP = {
    "high": "বেশি",
    "low": "কম",
    "normal": "স্বাভাবিক"
}


MEDICAL_TERMS = {
    "ESTIMATED AVERAGE GLUCOSE (EAG)": "গড় রক্তে শর্করার মাত্রা (EAG)",
    "BLOOD UREA NITROGEN": "রক্তে ইউরিয়া নাইট্রোজেন",
    "VITAMIN B12": "ভিটামিন বি১২",
    "TRIGLYCERIDES": "রক্তে ট্রাইগ্লিসারাইড বা চর্বির মাত্রা",
    "VLDL CHOLESTEROL": "ভিএলডিএল (VLDL) কোলেস্টেরল",
    "PCV": "পিসিভি (PCV) বা রক্তের পরিমাণ সূচক",
    "VITAMIN D (25 - OH VITAMIN D)": "ভিটামিন ডি",
    "HBA1C, GLYCATED HEMOGLOBIN": "গত কয়েক মাসের গড় সুগার মাত্রা",
    "UREA": "ইউরিয়া",
}


# =========================================================
# GOOGLE TRANSLATE
# =========================================================

def translate_text(text: str, target="bn") -> str:

    if not text.strip():
        return ""

    result = translate_client.translate(
        text,
        target_language=target,
        format_="text"
    )

    return result["translatedText"]


# =========================================================
# OLLAMA CALL
# =========================================================

def refine_with_ollama(prompt: str) -> str:

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload
    )

    response.raise_for_status()

    result = response.json()

    return result["response"].strip()


# =========================================================
# NUMBER VALIDATION
# =========================================================

def extract_numbers(text):

    return re.findall(
        r'\d+(?:\.\d+)?',
        text
    )


def validate_numbers(original, final):

    original_nums = extract_numbers(original)
    final_nums = extract_numbers(final)

    missing = []

    for num in original_nums:
        if num not in final_nums:
            missing.append(num)

    return list(set(missing))


# =========================================================
# BUILD FINAL MARKDOWN
# =========================================================

def build_bengali_markdown(data):

    patient = data["patient"]

    lines = []

    # =====================================================
    # HEADER
    # =====================================================

    lines.append("# মেডিকেল রিপোর্ট\n")

    # =====================================================
    # PATIENT INFO
    # =====================================================

    lines.append("## রোগীর তথ্য")

    lines.append(
        f"- নাম: {patient.get('name', 'N/A')}"
    )

    lines.append(
        f"- বয়স: {patient.get('age', 'N/A')}"
    )

    gender = GENDER_MAP.get(
        patient.get("gender"),
        patient.get("gender")
    )

    lines.append(f"- লিঙ্গ: {gender}")

    lines.append(
        f"- রোগী আইডি: "
        f"{patient.get('patient_id') or 'Not available'}"
    )

    lines.append(
        f"- রিপোর্টের তারিখ: "
        f"{patient.get('report_date', 'N/A')}\n"
    )

    # =====================================================
    # TEST RESULTS
    # =====================================================

    lines.append("## টেস্ট ফলাফল")

    for test in data.get("test_results", []):

        original_name = test["test_name"]

        translated_name = MEDICAL_TERMS.get(
            original_name,
            original_name
        )

        status = STATUS_MAP.get(
            test["status"],
            test["status"]
        )

        lines.append(
            f"- {translated_name}: "
            f"{test['value']} {test['unit']} "
            f"({status}) | "
            f"Range: {test['reference_range']}"
        )

    lines.append("")

    # =====================================================
    # AI EXPLANATION
    # =====================================================

    lines.append("## বিস্তারিত রিপোর্ট ব্যাখ্যা")

    for explanation in data.get("ai_explanation", []):

        translated = translate_text(explanation)

        refined = refine_with_ollama(
            f"""
You are a Bengali medical writer.

TASK:
Rewrite this into clean, natural Bengali.

RULES:
- Preserve ALL numbers exactly
- Preserve ALL units exactly
- Preserve medical meaning
- Do not hallucinate
- One sentence only
- No markdown
- Keep response concise

TEXT:
{translated}
"""
        )

        lines.append(f"- {refined}")

    lines.append("")

    # =====================================================
    # DOCTOR SUGGESTIONS
    # =====================================================

    lines.append("## ডাক্তারের পরামর্শ")

    for step in data.get("suggested_steps", []):

        translated = translate_text(step)

        refined = refine_with_ollama(
            f"""
You are a Bengali medical writer.

TASK:
Convert this into simple Bengali advice.

RULES:
- Preserve meaning
- No hallucination
- One sentence only
- No markdown

TEXT:
{translated}
"""
        )

        lines.append(f"- {refined}")

    lines.append("")

    # =====================================================
    # IMPRESSIONS
    # =====================================================

    if data.get("impressions"):

        lines.append("## সম্ভাব্য স্বাস্থ্য পর্যবেক্ষণ")

        for impression in data["impressions"]:

            translated = translate_text(impression)

            refined = refine_with_ollama(
                f"""
Translate this medical condition into Bengali.

RULES:
- Keep English term in brackets
- One line only
- No markdown

TEXT:
{translated}
"""
            )

            lines.append(f"- {refined}")

    lines.append("")

    # =====================================================
    # SIMPLE AI SUMMARY
    # =====================================================

    lines.append("## সহজ ভাষায় AI সারাংশ")

    combined_summary = "\n".join(
        data.get("ai_explanation", [])
    )

    translated_summary = translate_text(
        combined_summary
    )

    simple_summary = refine_with_ollama(
        f"""
You are a Bengali medical assistant.

TASK:
Write a simple patient-friendly Bengali summary.

RULES:
- Simple Bengali
- Short paragraph
- No hallucination
- No markdown
- Mention only major abnormalities

TEXT:
{translated_summary}
"""
    )

    lines.append(simple_summary)

    lines.append("")

    # =====================================================
    # DISCLAIMER
    # =====================================================

    lines.append("## সতর্কীকরণ\n")

    lines.append(
        "এই রিপোর্টটি শুধুমাত্র তথ্যগত সহায়তার জন্য। "
        "চিকিৎসার সিদ্ধান্ত নেওয়ার আগে অবশ্যই ডাক্তারকে দেখান।"
    )

    return "\n".join(lines)


# =========================================================
# MAIN
# =========================================================

def main():

    print("\nLoading summary.json...\n")

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Generating Bengali markdown...\n")

    final_md = build_bengali_markdown(data)

    # =====================================================
    # VALIDATE NUMBERS
    # =====================================================

    original_json_text = json.dumps(
        data,
        ensure_ascii=False
    )

    missing_numbers = validate_numbers(
        original_json_text,
        final_md
    )

    if missing_numbers:

        print("\nWARNING:")
        print("Possible missing numbers detected:\n")

        for num in missing_numbers:
            print(num)

    # =====================================================
    # SAVE FILE
    # =====================================================

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(final_md)

    print(
        f"\nSaved Bengali markdown to:\n{OUTPUT_MD}\n"
    )


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    main()