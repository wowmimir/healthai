import os
import json

from pathlib import Path
from typing import TypedDict, List, Dict

import fitz

from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END

from langchain_ollama import ChatOllama


# =========================================================
# PYDANTIC SCHEMAS
# =========================================================

class Medication(BaseModel):

    name: str = Field(
        description="Exact medicine name"
    )

    dosage_amount: str = Field(
        description="Quantity and frequency only"
    )

    intake_timing: str = Field(
        description="Morning/Night/etc"
    )

    food_relation: str = Field(
        description="Before food / After food"
    )

    duration_days: str = Field(
        description="Treatment duration"
    )


class PrescriptionData(BaseModel):

    patient: Dict = Field(
        default_factory=dict
    )

    doctor: Dict = Field(
        default_factory=dict
    )

    diagnosis: List[str] = Field(
        default_factory=list
    )

    vitals: Dict = Field(
        default_factory=dict
    )

    medications: List[Medication]

    prescribed_tests: List[str]

    dietary_advice: List[str]

    follow_up: str


# =========================================================
# LANGGRAPH STATE
# =========================================================

class PrescriptionState(TypedDict, total=False):

    pdf_path: str

    raw_text: str

    structured_data: dict

    markdown_output: str


# =========================================================
# OLLAMA
# =========================================================

llm = ChatOllama(
    model="gemma4:31b-cloud",
    temperature=0.1
)


# =========================================================
# OCR CLEANING
# =========================================================

def clean_text(text: str) -> str:

    lines = text.splitlines()

    cleaned = []

    garbage_patterns = [
        "Image not found",
        "type unknown",
    ]

    for line in lines:

        line = line.strip()

        if not line:
            continue

        skip = False

        for pattern in garbage_patterns:

            if pattern.lower() in line.lower():
                skip = True
                break

        if skip:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# =========================================================
# NODE 1 — PDF EXTRACTION
# =========================================================

def extract_text_node(state: PrescriptionState):

    pdf_path = state["pdf_path"]

    path = Path(pdf_path)

    if not path.exists():

        raise FileNotFoundError(
            f"PDF not found: {path}"
        )

    extracted_chunks = []

    with fitz.open(str(path)) as doc:

        print(f"\nReading PDF: {path.name}")
        print(f"Pages detected: {len(doc)}")

        for page_num, page in enumerate(
            doc,
            start=1
        ):

            text = page.get_text("text")

            if text.strip():

                extracted_chunks.append(
                    f"\n--- PAGE {page_num} ---\n{text}"
                )

    combined_text = "\n".join(
        extracted_chunks
    )

    combined_text = clean_text(
        combined_text
    )

    print("\n[TEXT EXTRACTION COMPLETE]")

    return {
        "raw_text": combined_text
    }


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are a medical prescription extraction assistant.

Extract ALL medically relevant information.

STRICT RULES:

1. Return ONLY valid JSON
2. No markdown
3. No explanations
4. No prose outside JSON
5. Preserve medicine names exactly
6. Never hallucinate information
7. If information missing:
   use "Not specified"

Extract:

- Patient info
- Doctor info
- Diagnosis
- Vitals
- Medications
- Tests
- Dietary advice
- Follow-up

Medication rules:

dosage_amount:
ONLY quantity/frequency

Examples:
"1 tablet twice daily"

intake_timing:
ONLY timing

Examples:
"Morning"
"Night"

food_relation:
ONLY food instruction

Examples:
"After food"
"Before breakfast"

duration_days:
ONLY duration

Examples:
"5 days"

REQUIRED JSON FORMAT:

{
  "patient": {
    "name": "",
    "age": "",
    "sex": ""
  },

  "doctor": {
    "name": "",
    "specialization": "",
    "registration_number": ""
  },

  "diagnosis": [],

  "vitals": {
    "bp": "",
    "rbs": "",
    "height": "",
    "weight": "",
    "temperature": ""
  },

  "medications": [
    {
      "name": "",
      "dosage_amount": "",
      "intake_timing": "",
      "food_relation": "",
      "duration_days": ""
    }
  ],

  "prescribed_tests": [],

  "dietary_advice": [],

  "follow_up": ""
}
"""


# =========================================================
# NODE 2 — STRUCTURED PARSING
# =========================================================

def parse_prescription_node(
    state: PrescriptionState
):

    raw_text = state["raw_text"]

    prompt = f"""
{SYSTEM_PROMPT}

Prescription Text:

{raw_text}
"""

    print(
        "\nSending prescription to Gemma..."
    )

    response = llm.invoke(prompt)

    content = response.content.strip()

    # ============================================
    # REMOVE MARKDOWN FENCES
    # ============================================

    content = content.replace(
        "```json",
        ""
    )

    content = content.replace(
        "```",
        ""
    ).strip()

    # ============================================
    # PARSE JSON
    # ============================================

    try:

        structured_data = json.loads(
            content
        )

    except Exception as e:

        print("\n========== RAW MODEL OUTPUT ==========\n")

        print(content)

        print("\n======================================\n")

        raise Exception(
            f"JSON parsing failed: {e}"
        )

    print(
        "\n[STRUCTURED EXTRACTION COMPLETE]"
    )

    return {
        "structured_data": structured_data
    }


# =========================================================
# NODE 3 — MARKDOWN GENERATION
# =========================================================

def markdown_node(state: PrescriptionState):

    data = state["structured_data"]

    markdown = (
        "# 📋 Patient Care Plan "
        "& Medication Guide\n\n"
    )

    markdown += (
        "Please follow the guidelines below "
        "closely. Do not skip or change "
        "medications without consulting "
        "your doctor.\n\n"
    )

    # =====================================================
    # PATIENT
    # =====================================================

    patient = data.get("patient", {})

    markdown += "## 👤 Patient Information\n\n"

    markdown += (
        f"- Name: "
        f"{patient.get('name', 'Not specified')}\n"
    )

    markdown += (
        f"- Age: "
        f"{patient.get('age', 'Not specified')}\n"
    )

    markdown += (
        f"- Sex: "
        f"{patient.get('sex', 'Not specified')}\n"
    )

    markdown += "\n---\n\n"

    # =====================================================
    # DIAGNOSIS
    # =====================================================

    markdown += "## 🩺 Diagnosis\n\n"

    diagnosis = data.get(
        "diagnosis",
        []
    )

    if diagnosis:

        for item in diagnosis:
            markdown += f"- {item}\n"

    else:

        markdown += "- Not specified\n"

    markdown += "\n---\n\n"

    # =====================================================
    # VITALS
    # =====================================================

    markdown += "## ❤️ Vitals\n\n"

    vitals = data.get("vitals", {})

    for key, value in vitals.items():

        markdown += (
            f"- {key.upper()}: {value}\n"
        )

    markdown += "\n---\n\n"

    # =====================================================
    # MEDICATIONS
    # =====================================================

    markdown += (
        "## 💊 Your Medicine Schedule\n\n"
    )

    markdown += (
        "| Medicine Name "
        "| Dosage Instructions "
        "| Food Timing "
        "| Duration |\n"
    )

    markdown += (
        "| :--- | :--- | :--- | :--- |\n"
    )

    for med in data.get(
        "medications",
        []
    ):

        markdown += (
            f"| **{med['name']}** "
            f"| {med['dosage_amount']} "
            f"| {med['intake_timing']} "
            f"({med['food_relation']}) "
            f"| 🗓️ {med['duration_days']} |\n"
        )

    markdown += "\n---\n\n"

    # =====================================================
    # DIETARY
    # =====================================================

    markdown += (
        "## 🍏 Dietary Guidelines\n\n"
    )

    dietary = data.get(
        "dietary_advice",
        []
    )

    if dietary:

        for advice in dietary:
            markdown += f"- {advice}\n"

    else:

        markdown += (
            "- No dietary advice provided.\n"
        )

    markdown += "\n---\n\n"

    # =====================================================
    # TESTS
    # =====================================================

    markdown += (
        "## 🧪 Prescribed Tests\n\n"
    )

    tests = data.get(
        "prescribed_tests",
        []
    )

    if tests:

        for test in tests:
            markdown += f"- {test}\n"

    else:

        markdown += (
            "- No tests prescribed.\n"
        )

    markdown += "\n---\n\n"

    # =====================================================
    # FOLLOW UP
    # =====================================================

    markdown += (
        "## 📆 Follow-Up "
        "& Next Review\n\n"
    )

    markdown += (
        f"**Next Scheduled Visit:** "
        f"{data.get('follow_up', 'As advised by doctor')}\n"
    )

    markdown += "\n---\n\n"

    # =====================================================
    # DOCTOR
    # =====================================================

    doctor = data.get("doctor", {})

    markdown += "## 👨‍⚕️ Doctor Information\n\n"

    markdown += (
        f"- Name: "
        f"{doctor.get('name', 'Not specified')}\n"
    )

    markdown += (
        f"- Specialization: "
        f"{doctor.get('specialization', 'Not specified')}\n"
    )

    markdown += (
        f"- Registration Number: "
        f"{doctor.get('registration_number', 'Not specified')}\n"
    )

    print(
        "\n[MARKDOWN GENERATION COMPLETE]"
    )

    return {
        "markdown_output": markdown
    }


# =========================================================
# LANGGRAPH PIPELINE
# =========================================================

builder = StateGraph(
    PrescriptionState
)

builder.add_node(
    "extract_text",
    extract_text_node
)

builder.add_node(
    "parse_prescription",
    parse_prescription_node
)

builder.add_node(
    "generate_markdown",
    markdown_node
)

builder.set_entry_point(
    "extract_text"
)

builder.add_edge(
    "extract_text",
    "parse_prescription"
)

builder.add_edge(
    "parse_prescription",
    "generate_markdown"
)

builder.add_edge(
    "generate_markdown",
    END
)

graph = builder.compile()


# =========================================================
# SAVE JSON
# =========================================================

def save_json(data: dict):

    output_dir = "outputs"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_path = os.path.join(
        output_dir,
        "prescription.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    return output_path


# =========================================================
# SAVE MARKDOWN
# =========================================================

def save_markdown(content: str):

    output_dir = "outputs"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_path = os.path.join(
        output_dir,
        "prescription.md"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)

    return output_path


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    try:

        result = graph.invoke({

            "pdf_path": "data/peerless.pdf"

        })

        structured_data = result[
            "structured_data"
        ]

        markdown_content = result[
            "markdown_output"
        ]

        json_path = save_json(
            structured_data
        )

        markdown_path = save_markdown(
            markdown_content
        )

        print("\n================================")
        print("PIPELINE SUCCESS")
        print("================================")

        print(
            f"\nJSON saved to:\n{json_path}"
        )

        print(
            f"\nMarkdown saved to:\n"
            f"{markdown_path}"
        )

        print("\n================================")
        print("FINAL STRUCTURED JSON")
        print("================================\n")

        print(
            json.dumps(
                structured_data,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as e:

        print("\n[PIPELINE FAILURE]")
        print(e)