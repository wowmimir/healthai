# System Architecture, Library, and Model Analysis: healthai

## 🏗️ High-Level Architectural Analysis

### 1. Health Report Pipeline (Ingestion $\to$ Summary)
- **Flow**: `PDF` $\to$ `pymupdf` $\to$ `regex/heuristics` $\to$ `Ollama (gemma4)` $\to$ `JSON/MD`.
- **Library Stack**: `pymupdf`, `re`, `requests`.
- **Model**: `gemma4`.
- **Analysis**: This is a **deterministic-heavy** pipeline. It relies on coordinates and regex to structure data before the LLM sees it. While fast, it creates a "bottleneck of rigidity"—if the report layout changes, the LLM never gets the data because the regex fails first.

### 2. Prescription Pipeline (Ingestion $\to$ Summary)
- **Flow**: `PDF/Img` $\to$ `langchain-ollama` $\to$ `Pydantic` $\to$ `LangGraph` $\to$ `MD`.
- **Library Stack**: `langgraph`, `pydantic`, `langchain-ollama`.
- **Model**: `gemma4:31b-cloud`.
- **Analysis**: This is a **modern AI-native** pipeline. By using Pydantic and LangGraph, the "intelligence" is moved to the front. It is significantly more flexible than the report pipeline.

### 3 & 4. Translation Pipelines (Report & Prescription)
- **Flow**: `JSON` $\to$ `Google Translate API` $\to$ `Ollama (gemma4)` $\to$ `MD`.
- **Library Stack**: `google-cloud-translate`, `requests`.
- **Model**: `gemma4:31b-cloud` (used as a "polisher").
- **Analysis**: A **Hybrid Translation** strategy. Using Google Translate for the "bulk" and an LLM for "medical nuance" is a smart way to keep costs down while maintaining quality. However, these two pipelines are currently mirrored as separate scripts, creating redundant logic.

### 5. PDF Generation Pipeline
- **Flow**: `Markdown` $\to$ `markdown` (Lib) $\to$ `HTML` $\to$ `Playwright` (Chrome) $\to$ `PDF`.
- **Library Stack**: `markdown`, `playwright`.
- **Analysis**: This is the **"Heavyweight"** path. Using Playwright means launching a full headless browser to print a page. While it gives perfect CSS/Font control (essential for Bengali), it is the most resource-intensive part of the stack.

---

## 🚀 Recommendations for Reduction & Improvement

### 1. Simplify the PDF Pipeline (Complexity $\downarrow$)
The `MD $\to$ HTML $\to$ PDF` flow is elegant but heavy.
- **Alternative**: Consider **`WeasyPrint`**. It is a Python-based visual rendering engine that converts HTML/CSS to PDF *without* needing a full browser like Playwright. It supports CSS Paged Media and is much lighter for server/CLI environments.
- **Direct MD $\to$ PDF**: If complex CSS isn't needed, **`FPDF2`** can generate PDFs directly, though Bengali font handling is more challenging than in HTML.

### 2. Unify Orchestration (Maintenance $\downarrow$)
Current split between a "Script-based" world (Reports) and a "Graph-based" world (Prescriptions).
- **Suggestion**: Migrate the Health Report pipeline into **LangGraph**. Instead of `report.py` calling functions in a line, make it a graph. This allows the use of the same "State" pattern, facilitating the addition of "Verification" or "Retry" nodes.

### 3. Model Strategy (Quality $\uparrow$)
Reliance on `gemma4` for both extraction and synthesis.
- **Suggestion**: Implement **Model Tiering**.
    - **Extraction/Translation**: Keep `gemma4` (efficient, local/cloud).
    - **Medical Synthesis/Final Review**: Use **Claude 3.5 Sonnet or 4.0**. Medical summaries require high nuance and zero-hallucination thresholds. A final "Review" pass by a frontier model would significantly increase safety and professional tone.

### 4. Consolidate Translation (Redundancy $\downarrow$)
`transreport.py` and `transpresc.py` scripts mirror each other (`Translate $\to$ Refine $\to$ Build MD`).
- **Suggestion**: Create a single `TranslationService` in `src/utils` or `src/llm`. Pass the "Data Schema" and "Translation Map" as arguments to reduce code duplication.

## Summary Table

| Pipeline | Current Library/Model | Complexity | Suggested Change |
| :--- | :--- | :--- | :--- |
| **Report** | `pymupdf` / `gemma4` | High (Rigid) | Migrate to LangGraph + LLM Parsing |
| **Presc** | `LangGraph` / `gemma4` | Low (Flexible) | Add a Claude-powered Review node |
| **Trans** | `Google` / `gemma4` | Medium (Redundant) | Merge into a single Translation Service |
| **PDF** | `Playwright` / Chrome | Very High (Heavy) | Replace Playwright with `WeasyPrint` |