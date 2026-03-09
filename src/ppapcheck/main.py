from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ppapcheck.models import SubmissionPackage
from ppapcheck.services.sample_submissions import get_sample_submissions
from ppapcheck.services.validation_orchestrator import ValidationOrchestrator


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SAMPLE_DESCRIPTIONS = {
    "hybrid_blocked": "Hybrid PPAP + FAIR package with a revision mismatch, broken special-characteristic linkage, and incomplete accountability.",
    "ppap_ready_with_observations": "PPAP level 3 package that is structurally acceptable with advisory observations only.",
    "fai_conditional_low_confidence": "FAI package that is technically close but still requires manual review because extraction confidence is weak.",
}

app = FastAPI(
    title="PPAPcheck",
    version="0.1.0",
    description="Evidence-based PPAP and FAI compliance validation platform.",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def get_sample_catalog() -> dict[str, SubmissionPackage]:
    return get_sample_submissions()


def evaluate_package(package: SubmissionPackage):
    validator = ValidationOrchestrator()
    report = validator.validate(package)
    return validator, report


def load_sample(sample_id: str):
    package = get_sample_catalog().get(sample_id)
    if not package:
        raise HTTPException(status_code=404, detail=f"Unknown sample '{sample_id}'.")
    return package


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/samples")
def list_samples() -> list[dict[str, str]]:
    return [
        {"id": sample_id, "description": SAMPLE_DESCRIPTIONS[sample_id]}
        for sample_id in get_sample_catalog()
    ]


@app.get("/api/samples/{sample_id}")
def get_sample_report(sample_id: str):
    package = load_sample(sample_id)
    _, report = evaluate_package(package)
    return report


@app.get("/api/samples/{sample_id}/audit-log")
def get_sample_audit_log(sample_id: str):
    package = load_sample(sample_id)
    validator, _ = evaluate_package(package)
    return validator.audit_log.get_entries(package.submission_id)


@app.get("/api/samples/{sample_id}/expert-report")
def download_sample_expert_report(sample_id: str) -> PlainTextResponse:
    package = load_sample(sample_id)
    _, report = evaluate_package(package)
    headers = {
        "Content-Disposition": f'attachment; filename="{sample_id}_expert_report.md"'
    }
    return PlainTextResponse(report.expert_report, headers=headers, media_type="text/markdown")


@app.post("/api/validate")
def validate_submission(package: SubmissionPackage):
    _, report = evaluate_package(package)
    return report


@app.get("/")
def reviewer_dashboard(request: Request, sample: str = "hybrid_blocked"):
    package = load_sample(sample)
    _, report = evaluate_package(package)
    report_json = json.dumps(report.model_dump(mode="json"), indent=2)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sample_id": sample,
            "sample_options": [
                {
                    "id": sample_id,
                    "description": SAMPLE_DESCRIPTIONS[sample_id],
                    "selected": sample_id == sample,
                }
                for sample_id in get_sample_catalog()
            ],
            "report": report,
            "report_json": report_json,
        },
    )
