# Healthcare AI System Architecture Analysis

## 1. Project Overview

`healthai` is an AI-assisted healthcare document intelligence system for digitally generated medical PDFs. It processes lab reports and e-prescriptions, extracts structured clinical information, generates patient-facing medical summaries, localizes outputs into Bengali, and renders Markdown/HTML/PDF-ready documents.

The current workflow is:

```text
PDF Text Extraction
-> Cleaning / Parsing
-> Structured JSON Extraction
-> AI Summarization or Refinement
-> Bengali Localization
-> Markdown Generation
-> HTML / PDF Rendering
```

The project no longer depends on OCR. It uses PyMuPDF (`fitz`) to extract text from machine-readable PDFs. This is an important architectural decision: it makes the pipeline faster and simpler than OCR-based systems, but also means scanned documents, image-only prescriptions, and malformed PDFs are outside the reliable processing envelope unless a separate fallback is added.

The system has two main document paths:

| Pipeline | Current Flow | Architectural Style |
|---|---|---|
| Lab report | PyMuPDF -> cleaner -> regex/heuristic parser -> Ollama summary -> JSON/Markdown/PDF | Deterministic-first with LLM support |
| Prescription | PyMuPDF -> LangGraph -> Gemma extraction -> JSON -> Markdown | LLM-first structured extraction |
| Bengali report | JSON -> Google Translate -> Gemma refinement -> Bengali Markdown | Hybrid machine translation plus LLM polishing |
| Bengali prescription | JSON -> maps/Translate/Gemma -> Bengali Markdown | Template plus translation/refinement |
| PDF rendering | Markdown -> HTML -> Playwright PDF, plus a simpler ReportLab path | Deterministic document rendering |


## 2. Concise Dependency Analysis

| Dependency / Component | Purpose | Strength | Key Limitation | Recommended Improvement |
|---|---|---|---|---|
| PyMuPDF / `fitz` | Extract text from digital PDFs | Fast, lightweight, good for machine-readable PDFs | Layout-sensitive; weak for scanned or malformed PDFs | Add extraction quality checks and clear fallback/error states |
| LangGraph | Prescription pipeline orchestration | Good foundation for staged AI workflows | Current graph is linear and lacks validation/retry/review nodes | Add validation, retry, confidence, and human-review nodes |
| LangChain / `langchain-ollama` | Connects code to Ollama chat model | Simplifies local model calls | Adds abstraction and model-response variability | Standardize model wrapper and response validation |
| Ollama | Local/self-hosted model serving | Privacy, local control, reduced API dependence | GPU/memory/concurrency bottleneck | Add queueing, model health checks, and deployment sizing |
| Gemma / `gemma4:31b-cloud` | Extraction, summarization, Bengali refinement | Cost-effective and local/cloud friendly | Lower reliability than frontier models for high-risk medical extraction | Use for low/medium-risk tasks; add frontier-model or human review for critical outputs |
| Google Cloud Translate API | Bengali translation | Scalable, strong general translation | Medical nuance, dosage wording, and localization may drift | Add medical glossary, terminology lock, and translation QA |
| Pydantic | Defines prescription schema intent | Useful for typed structured outputs | Parsed LLM JSON is not consistently validated into models | Enforce schema validation after every model extraction |
| `requests` / `urllib` | Direct Ollama/API calls | Simple and transparent | Limited retry, timeout, and error classification | Centralize API client with retries, timeouts, and logging |
| Markdown | Intermediate document format | Portable, readable, easy to render | Tables/fonts/layout can vary across renderers | Keep templates deterministic and test rendered outputs |
| Playwright | HTML-to-PDF rendering | High-fidelity PDF with Bengali font support | Heavyweight; browser startup cost affects scale | Use worker pool or evaluate WeasyPrint for lighter rendering |
| ReportLab | Direct PDF generation utility | Lightweight Python PDF path | Bengali/table rendering needs careful font support | Use only for simple PDFs unless font/layout support is improved |
| Local JSON/file artifacts | Store pipeline outputs | Simple and demo-friendly | Not suitable for multi-user production or audit workflows | Move to database/object storage with job IDs and schema versions |



## 3. Pipeline Architecture Analysis


Key architectural strengths:

| Strength | Why It Matters |
|---|---|
| JSON-first pipeline | Enables validation, localization, rendering, API integration, and auditing |
| Deterministic templates | Reduces risk of values changing during final document generation |
| Modular pipeline stages | Allows future replacement of extraction, translation, or rendering layers |
| Local model option | Improves privacy and reduces dependence on external LLM APIs |
| Bengali output path | Supports patient-facing multilingual healthcare communication |

Key weaknesses:

| Weakness | Risk | Recommended Fix |
|---|---|---|
| No schema versioning | Future JSON changes may break renderers/translators | Add `schema_version` to all outputs |
| Limited validation | LLM or parser errors may reach final documents | Enforce Pydantic validation and field-level checks |
| No confidence scoring | Users cannot tell which fields are uncertain | Add extraction confidence and review flags |
| Limited retry handling | Temporary Ollama/API failures can fail the pipeline | Centralize retries, timeouts, and fallback states |
| No audit trail | Hard to explain how a medical output was produced | Store source text, parsed JSON, model name, prompt version, and timestamp |
| Duplicated translation/rendering scripts | Higher maintenance cost and inconsistent behavior | Consolidate shared translation and rendering services |
| Mostly synchronous execution | Poor fit for batch processing or concurrent users | Add job queue and background workers |
| Hardcoded paths/config | Difficult deployment and multi-environment setup | Use config/env-based path and credential management |


## 4. Model Analysis

### Gemma via Ollama

Gemma is used for summarization, prescription extraction, and Bengali text refinement. This is a reasonable cost-conscious model strategy. It supports local or self-hosted workflows and reduces dependence on commercial LLM APIs.

The tradeoff is reliability. Medical extraction requires high precision, especially for prescriptions. A single dosage, frequency, or duration error can create patient safety risk. Gemma can be useful for controlled tasks, but it should not be treated as clinically reliable without validation, evaluation data, and human review for high-risk outputs.

### Google Cloud Translate API

Google Translate provides scalable Bengali translation. It is useful for broad language coverage and reduces the burden on the LLM. However, medical Bengali is not just general translation. Dosage instructions, food timing, units, and disease names require domain-specific consistency. The project already uses some static maps, which is a good start, but production use needs a controlled medical glossary and translation QA.

### Local vs Hosted Inference

| Choice | Advantage | Weakness | Best Use |
|---|---|---|---|
| Local/Ollama models | Privacy, lower marginal cost, local control | GPU/memory ops burden, slower scaling, variable reliability | Development, low-volume deployments, privacy-sensitive workflows |
| Hosted frontier models | Higher reasoning and structured-output reliability | API cost, data-sharing concerns, vendor dependency | Critical extraction, final review, safety-sensitive summaries |
| Hybrid model routing | Balances cost and quality | More complex orchestration | Production systems with risk-based escalation |

### Gemma vs GPT-4-Class / Claude-Class Models

Gemma is attractive for cost control, local deployment, and experimentation. GPT-4-class and Claude-class models are generally stronger for instruction following, structured extraction, long-context reasoning, and nuanced medical language. The downside is cost, API dependency, and privacy/compliance review.

The realistic production strategy is not “local or cloud only.” A stronger architecture would route low-risk formatting and refinement to local models, while sending high-risk extraction failures or uncertain cases to a stronger hosted model or human reviewer.


## 5. Performance & Scalability Analysis

At small scale, the current architecture is practical. A developer or demo environment can process a few PDFs, call Ollama locally, translate with Google, and render PDFs through Playwright.

At production scale, several bottlenecks appear:

| Component | Bottleneck | Scaling Risk |
|---|---|---|
| PyMuPDF extraction | CPU and PDF layout variability | Usually manageable, but needs batch error handling |
| Ollama/Gemma | GPU memory, model load time, concurrent inference | Main throughput bottleneck |
| Google Translate | External API latency and cost | Adds dependency on network and cloud billing |
| Playwright PDF rendering | Browser startup and memory usage | Heavy for concurrent PDF jobs |
| Local file outputs | No job isolation or access control | Not suitable for multi-user production |
| Synchronous scripts | One job at a time | Poor user experience for large batches |


## 6. Improvement Roadmap

### Short Term

| Area | Improvement |
|---|---|
| Validation | Enforce Pydantic validation after every JSON extraction |
| Reliability | Add retries, timeouts, and clear failure states for Ollama and Google Translate |
| Safety | Add confidence/review flags for missing, uncertain, or model-generated fields |
| Testing | Add golden-file tests for sample PDFs, JSON outputs, Markdown, and number preservation |
| Maintainability | Consolidate duplicated translation and PDF rendering logic |
| Configuration | Move hardcoded paths, model names, and credential locations into config/env |
| Auditability | Log model name, prompt version, input file, output file, and pipeline status |

### Mid Term

| Area | Improvement |
|---|---|
| Orchestration | Move both lab report and prescription workflows into a consistent graph/job architecture |
| Schema management | Add `schema_version` and migration strategy for JSON outputs |
| Storage | Replace local-only artifacts with database records and object storage |
| Batch processing | Add async queue workers for extraction, inference, translation, and rendering |
| Localization | Add Bengali medical glossary and locked translations for dosages, units, and common terms |
| Model routing | Add fallback to stronger model or human review when confidence is low |
| Observability | Add structured logs, metrics, job status, and failure dashboards |

### Long Term

| Area | Improvement |
|---|---|
| Clinical safety | Build clinician-reviewed evaluation datasets and acceptance thresholds |
| Compliance | Add PHI protection, access control, encryption, retention policies, and audit logs |
| Human-in-the-loop | Add review UI for uncertain extractions and high-risk prescription fields |
| Scalable inference | Deploy dedicated inference server or managed model endpoint |
| Quality assurance | Track extraction accuracy, translation quality, rendering defects, and model drift |
| Enterprise readiness | Add API authentication, tenant isolation, monitoring, backups, and deployment automation |


## 7. Presentation-Ready Summary Tables

### Dependency Summary

| Dependency | Purpose | Limitation | Suggested Improvement |
|---|---|---|---|
| PyMuPDF | Digital PDF text extraction | Sensitive to layout and malformed PDFs | Add extraction quality checks |
| LangGraph | Pipeline orchestration | Currently linear and underused | Add validation/retry/review nodes |
| Ollama | Local model serving | GPU/concurrency bottleneck | Add queueing and health checks |
| Gemma | Extraction/summarization/refinement | Lower reliability for high-risk medical tasks | Use with validation and escalation |
| Google Translate | Bengali translation | Medical meaning may drift | Add glossary and QA |
| Pydantic | Schema definition | Not fully enforced after LLM output | Validate every output |
| Playwright | PDF rendering | Heavy at scale | Use worker pool or lighter renderer |
| Markdown | Portable document format | Rendering can vary | Template and output tests |

### Architecture Risk Summary

| Architecture Component | Current Risk | Business Impact | Recommended Fix |
|---|---|---|---|
| PDF extraction | Missing or reordered text | Incorrect downstream JSON | Add extraction validation |
| LLM extraction | Hallucinated or malformed JSON | Patient safety and trust risk | Schema validation and confidence flags |
| Translation | Dosage/term drift | Misunderstood instructions | Medical glossary and locked terms |
| Rendering | Layout/font issues | Unprofessional or unclear output | Render tests and font checks |
| Storage | Local files only | Poor multi-user readiness | Database and object storage |
| Orchestration | Synchronous scripts | Low throughput | Async job queue |
| Monitoring | Minimal logs | Hard to debug or audit | Structured observability |

### Model Choice Summary

| Model Choice | Advantage | Weakness | Better Alternative / Upgrade |
|---|---|---|---|
| Gemma via Ollama | Private, lower cost, controllable | Reliability and latency constraints | Add validation and risk-based escalation |
| Google Translate | Scalable translation | Medical nuance may be inconsistent | Glossary-backed translation |
| Frontier LLM API | Better structured reasoning | Higher cost and vendor dependency | Use selectively for review/high-risk cases |
| Hybrid routing | Balances cost and quality | More orchestration complexity | Best long-term production strategy |

### Local vs Cloud

| Option | Cost | Reliability | Scalability |
|---|---|---|---|
| Local/Ollama | Low marginal cost, hardware upfront | Depends on local ops and model quality | Limited by GPU/memory |
| Cloud LLM API | Pay-per-use | Stronger managed reliability | Scales easily but can be expensive |
| Hybrid | Optimized by risk level | Best balance if well-designed | Requires routing and monitoring |

### Current Pipeline Evolution

| Current Pipeline | Limitation | Future Improvement |
|---|---|---|
| Lab report parser | Layout-specific heuristics | Add schema validation and broader parser coverage |
| Prescription parser | LLM-dependent extraction | Add validation, confidence, and review |
| Bengali translation | Mixed maps, Translate, and LLM refinement | Centralize localization service |
| Markdown/PDF generation | Duplicate scripts | Shared deterministic rendering module |
| Local outputs | Demo-friendly only | Job database and object storage |