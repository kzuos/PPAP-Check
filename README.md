# PPAPcheck

PPAPcheck is an evidence-based submission validation platform for PPAP, FAI, and hybrid PPAP + FAIR packages. It is designed to behave like a strict senior quality reviewer, not a chatbot. The service validates document presence, mandatory field completeness, cross-document consistency, traceability, technical credibility, and manual-review risk before a supplier submission is released to an OEM or customer.

## What this first slice delivers

- A modular validation pipeline with explicit services for ingestion, classification, extraction normalization, standards rules, consistency checking, traceability, scoring, reporting, and audit logging.
- A strict machine-readable output that matches the requested sections:
  - `submission_mode`
  - `overall_decision`
  - `overall_score`
  - `confidence`
  - `document_inventory`
  - `required_documents`
  - `missing_documents`
  - `metadata_master_record`
  - `cross_document_conflicts`
  - `ppap_checks`
  - `fai_checks`
  - `traceability_checks`
  - `technical_findings`
  - `nonconformities`
  - `manual_review_flags`
  - `recommended_actions`
  - `expert_report`
- A reviewer dashboard that shows inventory, missing documents, severity-coded findings, traceability checks, the expert report, and the raw JSON report.
- Sample evidence sets that exercise `BLOCK_SUBMISSION`, `PASS_WITH_OBSERVATIONS`, and `CONDITIONAL`.

## Architecture

The current implementation is framework-light but production-oriented. The validation engine is independent of the web routes, so the same logic can back APIs, worker jobs, and a future human-review queue.

### Service boundaries

- `document_ingestion_service`: normalizes incoming document records and assigns stable IDs.
- `document_classifier`: infers document type when the caller cannot supply one.
- `extraction_service`: normalizes extracted metadata without inventing evidence.
- `standards_rule_engine`: enforces required document presence and mandatory-field completeness.
- `cross_document_validator`: resolves a metadata master record and flags part, drawing, revision, supplier, customer, process, and material conflicts.
- `traceability_engine`: checks drawing-to-results coverage, process-flow linkage, and special-characteristic control coverage.
- `technical_quality_validator`: flags missing capability evidence, absent MSA support, incomplete measurement context, and PFMEA-to-Control Plan disconnects.
- `scoring_engine`: converts findings into decision and confidence.
- `report_generator`: builds the expert narrative and recommended actions.
- `audit_log_service`: records the validation stages for traceability.

### Current limits

- This slice validates normalized extracted data, not raw PDFs or OCR directly.
- No database is wired yet; sample submissions are in-memory fixtures.
- Customer-specific rules are supported as context inputs, but there is not yet a persistent customer-rule repository or template authoring UI.

Those limits are deliberate. The validation contract is separated from extraction so OCR, LLM extraction, document AI, or ERP integrations can be added without weakening the evidence rules.

## Project layout

```text
src/ppapcheck/
  main.py
  models.py
  services/
  templates/
  static/
tests/
```

## Run locally

1. Install dependencies:

```bash
python -m pip install -e .[dev]
```

2. Start the service:

```bash
python -m uvicorn ppapcheck.main:app --reload
```

3. Open the dashboard:

`http://127.0.0.1:8000/`

## API endpoints

- `GET /health`
- `GET /api/samples`
- `GET /api/samples/{sample_id}`
- `GET /api/samples/{sample_id}/audit-log`
- `GET /api/samples/{sample_id}/expert-report`
- `POST /api/validate`

## Next production steps

- Add persistent storage for submissions, uploaded documents, extracted fields, validation reports, traceability links, review comments, and billing events.
- Add OCR and document parsing adapters behind the extraction contract.
- Add customer-template management and rule packs.
- Add background processing, review assignment, and reviewer comments.
- Add authentication, audit retention, and tenant isolation.

