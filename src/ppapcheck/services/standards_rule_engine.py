from __future__ import annotations

from dataclasses import dataclass

from ppapcheck.models import (
    CheckResult,
    CheckStatus,
    DocumentInventoryItem,
    DocumentRecord,
    DocumentType,
    EvidenceRef,
    ExtractionStatus,
    PresenceStatus,
    RequirementStatus,
    Severity,
    SubmissionMode,
    SubmissionPackage,
    ValidationFinding,
)
from ppapcheck.services.requirement_catalog import FAI_KEY_TYPES, PPAP_KEY_TYPES, RequirementCatalog


MANDATORY_FIELDS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.PSW: (
        "part_number",
        "drawing_number",
        "revision",
        "customer_name",
        "supplier_name",
        "submission_reason",
        "approval_status",
        "signatory",
        "date",
    ),
    DocumentType.DESIGN_RECORD: ("part_number", "drawing_number", "revision"),
    DocumentType.PFMEA: ("part_number", "revision", "process_name"),
    DocumentType.PROCESS_FLOW: ("part_number", "revision", "process_name"),
    DocumentType.CONTROL_PLAN: ("part_number", "revision", "process_name"),
    DocumentType.MSA: ("part_number", "revision", "date"),
    DocumentType.DIMENSIONAL_RESULTS: ("part_number", "drawing_number", "revision", "date"),
    DocumentType.MATERIAL_RESULTS: ("part_number", "revision", "date"),
    DocumentType.PROCESS_STUDY: ("part_number", "revision", "date"),
    DocumentType.BALLOONED_DRAWING: ("part_number", "drawing_number", "revision"),
    DocumentType.FAIR: (
        "part_number",
        "drawing_number",
        "revision",
        "customer_name",
        "supplier_name",
        "approval_status",
        "signatory",
        "date",
    ),
    DocumentType.MATERIAL_CERTIFICATE: ("material", "date"),
}

FIELD_LABELS = {
    "part_number": "part number",
    "drawing_number": "drawing number",
    "revision": "revision",
    "customer_name": "customer name",
    "supplier_name": "supplier name",
    "submission_reason": "submission reason",
    "approval_status": "approval status",
    "signatory": "signatory",
    "date": "date",
    "process_name": "process name",
    "material": "material",
}


@dataclass
class StandardsEvaluation:
    required_documents: list[RequirementStatus]
    document_inventory: list[DocumentInventoryItem]
    ppap_checks: list[CheckResult]
    fai_checks: list[CheckResult]
    nonconformities: list[ValidationFinding]
    manual_review_flags: list[ValidationFinding]


class StandardsRuleEngine:
    def __init__(self, requirement_catalog: RequirementCatalog) -> None:
        self.requirement_catalog = requirement_catalog

    def evaluate(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> StandardsEvaluation:
        requirement_statuses = self.requirement_catalog.build_requirement_statuses(package, mode)
        ppap_checks: list[CheckResult] = []
        fai_checks: list[CheckResult] = []
        nonconformities: list[ValidationFinding] = []
        manual_review_flags: list[ValidationFinding] = []

        for requirement in requirement_statuses:
            if requirement.document_type in PPAP_KEY_TYPES:
                ppap_checks.append(self._requirement_to_check(requirement))
            if requirement.document_type in FAI_KEY_TYPES:
                fai_checks.append(self._requirement_to_check(requirement))
            if requirement.status == PresenceStatus.MISSING and requirement.severity_if_missing:
                nonconformities.append(
                    ValidationFinding(
                        finding_id=f"missing-{requirement.document_type.value.lower()}",
                        category="document_presence",
                        severity=requirement.severity_if_missing,
                        title=f"Missing required document: {requirement.document_label}",
                        description=(
                            f"{requirement.document_label} is required for this submission context but was not provided. "
                            f"Requirement basis: {requirement.requirement_source}."
                        ),
                        blocking=requirement.blocking_if_missing,
                        related_documents=[requirement.document_type],
                        confidence=0.98,
                        suggested_action=f"Provide the missing {requirement.document_label} before submission.",
                    )
                )

        document_inventory: list[DocumentInventoryItem] = []
        for document in package.documents:
            findings_for_document, manual_flags_for_document = self._validate_document(document)
            nonconformities.extend(findings_for_document)
            manual_review_flags.extend(manual_flags_for_document)
            document_inventory.append(
                DocumentInventoryItem(
                    file_name=document.file_name,
                    document_type=document.document_type,
                    document_label=document.document_label,
                    classification_confidence=document.classification_confidence,
                    key_metadata=self._key_metadata(document),
                    structured_counts=self._structured_counts(document),
                    findings=[finding.title for finding in findings_for_document + manual_flags_for_document],
                )
            )

        return StandardsEvaluation(
            required_documents=requirement_statuses,
            document_inventory=document_inventory,
            ppap_checks=ppap_checks,
            fai_checks=fai_checks,
            nonconformities=nonconformities,
            manual_review_flags=manual_review_flags,
        )

    def _requirement_to_check(self, requirement: RequirementStatus) -> CheckResult:
        if requirement.status == PresenceStatus.PRESENT:
            return CheckResult(
                check_id=f"presence-{requirement.document_type.value.lower()}",
                name=requirement.document_label,
                status=CheckStatus.PASS,
                description=f"{requirement.document_label} is present.",
                confidence=0.98,
            )
        if requirement.status == PresenceStatus.MISSING:
            return CheckResult(
                check_id=f"presence-{requirement.document_type.value.lower()}",
                name=requirement.document_label,
                status=CheckStatus.FAIL,
                severity=requirement.severity_if_missing,
                description=f"{requirement.document_label} is missing.",
                confidence=0.98,
                suggested_action=f"Provide the missing {requirement.document_label}.",
            )
        return CheckResult(
            check_id=f"presence-{requirement.document_type.value.lower()}",
            name=requirement.document_label,
            status=CheckStatus.UNCLEAR,
            description=f"{requirement.document_label} is optional or condition-dependent in the current baseline rules.",
            confidence=0.75,
        )

    def _validate_document(
        self, document: DocumentRecord
    ) -> tuple[list[ValidationFinding], list[ValidationFinding]]:
        findings: list[ValidationFinding] = []
        manual_review_flags: list[ValidationFinding] = []
        if document.classification_confidence < 0.75:
            manual_review_flags.append(
                ValidationFinding(
                    finding_id=f"classification-{document.document_id}",
                    category="classification",
                    severity=Severity.MINOR,
                    title=f"Document classification confidence is low for {document.file_name}",
                    description=(
                        f"{document.file_name} was classified as {document.document_label} with low confidence "
                        f"({document.classification_confidence:.2f})."
                    ),
                    related_documents=[document.document_type],
                    confidence=document.classification_confidence,
                    suggested_action="Confirm the document type classification before relying on downstream validation results.",
                )
            )

        for field_name in MANDATORY_FIELDS.get(document.document_type, ()):
            field = document.get_field(field_name)
            label = FIELD_LABELS.get(field_name, field_name.replace("_", " "))
            if field.is_present:
                if field.status in {
                    ExtractionStatus.INFERRED_LOW_CONFIDENCE,
                    ExtractionStatus.REQUIRES_MANUAL_REVIEW,
                    ExtractionStatus.NOT_LEGIBLE,
                    ExtractionStatus.INCONSISTENT,
                } or field.confidence < 0.65:
                    manual_review_flags.append(
                        ValidationFinding(
                            finding_id=f"manual-{document.document_id}-{field_name}",
                            category="manual_review",
                            severity=Severity.MINOR,
                            title=f"Low-confidence extraction for {label} in {document.file_name}",
                            description=(
                                f"{label.title()} in {document.file_name} is marked as '{field.status.value}' "
                                f"with confidence {field.confidence:.2f}."
                            ),
                            evidence=self._field_evidence(document, field_name, field.text, field.evidence),
                            related_documents=[document.document_type],
                            confidence=field.confidence,
                            suggested_action=f"Manually confirm the {label} value in {document.file_name}.",
                        )
                    )
                continue

            severity, blocking = self._missing_field_severity(document.document_type, field_name)
            findings.append(
                ValidationFinding(
                    finding_id=f"missing-field-{document.document_id}-{field_name}",
                    category="field_completeness",
                    severity=severity,
                    title=f"Mandatory field missing: {label.title()}",
                    description=(
                        f"{document.document_label} does not contain a verifiable {label}. "
                        "This mandatory field is required for document completeness."
                    ),
                    blocking=blocking,
                    evidence=self._field_evidence(document, field_name, label, field.evidence),
                    related_documents=[document.document_type],
                    confidence=0.97,
                    suggested_action=f"Update {document.file_name} to include a verifiable {label}.",
                )
            )

        for index, note in enumerate(document.notes, start=1):
            lowered_note = note.lower()
            if any(
                token in lowered_note
                for token in ("manual review", "ocr", "text extraction is sparse", "image-based", "text-poor")
            ):
                manual_review_flags.append(
                    ValidationFinding(
                        finding_id=f"manual-note-{document.document_id}-{index}",
                        category="manual_review",
                        severity=Severity.MINOR,
                        title=f"Manual review required for {document.file_name}",
                        description=note,
                        related_documents=[document.document_type],
                        confidence=min(document.classification_confidence, 0.62),
                        suggested_action="Review the referenced pages visually before relying on the extracted result.",
                    )
                )
                continue
            findings.append(
                ValidationFinding(
                    finding_id=f"observation-{document.document_id}-{index}",
                    category="document_observation",
                    severity=Severity.OBSERVATION,
                    title=f"Document observation in {document.file_name}",
                    description=note,
                    related_documents=[document.document_type],
                    confidence=0.82,
                )
            )

        return findings, manual_review_flags

    def _missing_field_severity(
        self, document_type: DocumentType, field_name: str
    ) -> tuple[Severity, bool]:
        if document_type in {DocumentType.PSW, DocumentType.FAIR} and field_name in {
            "signatory",
            "approval_status",
            "date",
        }:
            return Severity.CRITICAL, True
        if field_name in {"part_number", "drawing_number", "revision"} and document_type in {
            DocumentType.PSW,
            DocumentType.DESIGN_RECORD,
            DocumentType.BALLOONED_DRAWING,
            DocumentType.FAIR,
        }:
            return Severity.CRITICAL, True
        return Severity.MAJOR, False

    def _key_metadata(self, document: DocumentRecord) -> dict[str, str]:
        keys = ("part_number", "drawing_number", "revision", "customer_name", "supplier_name", "process_name", "material")
        metadata: dict[str, str] = {}
        for key in keys:
            value = document.get_text(key)
            if value:
                metadata[key] = value
        return metadata

    def _structured_counts(self, document: DocumentRecord) -> dict[str, int]:
        counts: dict[str, int] = {}
        if document.drawing_characteristics:
            counts["characteristics"] = len(document.drawing_characteristics)
        if document.inspection_results:
            counts["results"] = len(document.inspection_results)
        if document.certificates:
            counts["certificates"] = len(document.certificates)
        if document.process_flow_steps:
            counts["flow_steps"] = len(document.process_flow_steps)
        if document.pfmea_entries:
            counts["pfmea_rows"] = len(document.pfmea_entries)
        if document.control_plan_entries:
            counts["control_rows"] = len(document.control_plan_entries)
        if document.capability_studies:
            counts["capability_studies"] = len(document.capability_studies)
        if document.msa_studies:
            counts["msa_studies"] = len(document.msa_studies)
        return counts

    def _field_evidence(
        self,
        document: DocumentRecord,
        field_name: str,
        snippet: str,
        evidence: list[EvidenceRef],
    ) -> list[EvidenceRef]:
        if evidence:
            return evidence[:3]
        return [
            EvidenceRef(
                file_name=document.file_name,
                field_name=field_name,
                snippet=snippet,
                confidence=document.classification_confidence,
            )
        ]
