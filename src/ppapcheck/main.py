from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ppapcheck.models import SubmissionContext, SubmissionMode, SubmissionPackage
from ppapcheck.services.sample_submissions import get_sample_submissions
from ppapcheck.services.upload_submission_builder import UploadSubmissionBuilder
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


def sample_options(active_id: str) -> list[dict[str, str | bool]]:
    return [
        {
            "id": sample_id,
            "description": SAMPLE_DESCRIPTIONS[sample_id],
            "selected": sample_id == active_id,
        }
        for sample_id in get_sample_catalog()
    ]


def default_form_values() -> dict[str, str]:
    return {
        "customer_oem": "",
        "requested_submission_mode": SubmissionMode.UNKNOWN.value,
        "ppap_level": "",
        "part_number": "",
        "drawing_number": "",
        "revision": "",
        "supplier_name": "",
        "manufacturing_process": "",
        "material": "",
        "special_processes": "",
        "customer_specific_rules": "",
    }


def build_submission_context(form_values: dict[str, str]) -> SubmissionContext:
    requested_mode_raw = (form_values.get("requested_submission_mode") or SubmissionMode.UNKNOWN.value).upper()
    try:
        requested_mode = SubmissionMode(requested_mode_raw)
    except ValueError:
        requested_mode = SubmissionMode.UNKNOWN

    ppap_level_raw = (form_values.get("ppap_level") or "").strip()
    ppap_level = int(ppap_level_raw) if ppap_level_raw.isdigit() else None

    return SubmissionContext(
        customer_oem=(form_values.get("customer_oem") or "").strip() or None,
        requested_submission_mode=requested_mode,
        ppap_level=ppap_level,
        part_number=(form_values.get("part_number") or "").strip() or None,
        drawing_number=(form_values.get("drawing_number") or "").strip() or None,
        revision=(form_values.get("revision") or "").strip() or None,
        supplier_name=(form_values.get("supplier_name") or "").strip() or None,
        manufacturing_process=(form_values.get("manufacturing_process") or "").strip() or None,
        material=(form_values.get("material") or "").strip() or None,
        special_processes=[item.strip() for item in (form_values.get("special_processes") or "").split(",") if item.strip()],
        customer_specific_rules=[
            item.strip() for item in (form_values.get("customer_specific_rules") or "").split(",") if item.strip()
        ],
    )


async def build_uploaded_package(
    files: list[UploadFile],
    form_values: dict[str, str],
):
    uploaded_files: list[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            continue
        payload = await file.read()
        if not payload:
            continue
        uploaded_files.append((file.filename, payload))

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="At least one non-empty file is required.")

    context = build_submission_context(form_values)
    builder = UploadSubmissionBuilder()
    return builder.build(uploaded_files, context)


def render_dashboard(
    request: Request,
    report,
    *,
    sample_id: str,
    active_source: str,
    report_json: str,
    upload_warnings: list[str] | None = None,
    form_values: dict[str, str] | None = None,
    uploaded_files: list[str] | None = None,
    error_message: str | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "sample_id": sample_id,
            "sample_options": sample_options(sample_id),
            "report": report,
            "report_json": report_json,
            "active_source": active_source,
            "upload_warnings": upload_warnings or [],
            "form_values": form_values or default_form_values(),
            "uploaded_files": uploaded_files or [],
            "error_message": error_message,
        },
    )


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


@app.post("/api/validate-upload")
async def validate_uploaded_submission(
    files: list[UploadFile] = File(...),
    customer_oem: str = Form(""),
    requested_submission_mode: str = Form(SubmissionMode.UNKNOWN.value),
    ppap_level: str = Form(""),
    part_number: str = Form(""),
    drawing_number: str = Form(""),
    revision: str = Form(""),
    supplier_name: str = Form(""),
    manufacturing_process: str = Form(""),
    material: str = Form(""),
    special_processes: str = Form(""),
    customer_specific_rules: str = Form(""),
):
    form_values = {
        "customer_oem": customer_oem,
        "requested_submission_mode": requested_submission_mode,
        "ppap_level": ppap_level,
        "part_number": part_number,
        "drawing_number": drawing_number,
        "revision": revision,
        "supplier_name": supplier_name,
        "manufacturing_process": manufacturing_process,
        "material": material,
        "special_processes": special_processes,
        "customer_specific_rules": customer_specific_rules,
    }
    build_result = await build_uploaded_package(files, form_values)
    _, report = evaluate_package(build_result.package)
    return {"report": report, "upload_warnings": build_result.warnings}


@app.get("/")
def reviewer_dashboard(request: Request, sample: str = "hybrid_blocked"):
    package = load_sample(sample)
    _, report = evaluate_package(package)
    report_json = json.dumps(report.model_dump(mode="json"), indent=2)
    return render_dashboard(
        request,
        report,
        sample_id=sample,
        active_source="sample",
        report_json=report_json,
        form_values=default_form_values(),
    )


@app.post("/")
async def upload_dashboard(
    request: Request,
    files: list[UploadFile] | None = File(None),
    customer_oem: str = Form(""),
    requested_submission_mode: str = Form(SubmissionMode.UNKNOWN.value),
    ppap_level: str = Form(""),
    part_number: str = Form(""),
    drawing_number: str = Form(""),
    revision: str = Form(""),
    supplier_name: str = Form(""),
    manufacturing_process: str = Form(""),
    material: str = Form(""),
    special_processes: str = Form(""),
    customer_specific_rules: str = Form(""),
):
    files = files or []
    form_values = {
        "customer_oem": customer_oem,
        "requested_submission_mode": requested_submission_mode,
        "ppap_level": ppap_level,
        "part_number": part_number,
        "drawing_number": drawing_number,
        "revision": revision,
        "supplier_name": supplier_name,
        "manufacturing_process": manufacturing_process,
        "material": material,
        "special_processes": special_processes,
        "customer_specific_rules": customer_specific_rules,
    }
    try:
        build_result = await build_uploaded_package(files, form_values)
        _, report = evaluate_package(build_result.package)
        report_json = json.dumps(report.model_dump(mode="json"), indent=2)
        return render_dashboard(
            request,
            report,
            sample_id="hybrid_blocked",
            active_source="upload",
            report_json=report_json,
            upload_warnings=build_result.warnings,
            form_values=form_values,
            uploaded_files=[item.filename for item in files if item.filename],
        )
    except HTTPException as exc:
        sample_id = "hybrid_blocked"
        package = load_sample(sample_id)
        _, report = evaluate_package(package)
        report_json = json.dumps(report.model_dump(mode="json"), indent=2)
        return render_dashboard(
            request,
            report,
            sample_id=sample_id,
            active_source="sample",
            report_json=report_json,
            form_values=form_values,
            error_message=str(exc.detail),
        )
    except Exception as exc:  # pragma: no cover - defensive path for real uploads
        sample_id = "hybrid_blocked"
        package = load_sample(sample_id)
        _, report = evaluate_package(package)
        report_json = json.dumps(report.model_dump(mode="json"), indent=2)
        return render_dashboard(
            request,
            report,
            sample_id=sample_id,
            active_source="sample",
            report_json=report_json,
            form_values=form_values,
            error_message=f"Upload parsing failed: {exc}",
        )
