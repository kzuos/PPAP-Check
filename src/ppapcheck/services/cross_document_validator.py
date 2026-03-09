from __future__ import annotations

from collections import Counter

from ppapcheck.models import (
    DocumentRecord,
    DocumentType,
    EvidenceRef,
    ExtractionStatus,
    MetadataMasterRecord,
    Severity,
    SubmissionContext,
    SubmissionPackage,
    ValidationFinding,
)


FIELD_KEY_MAP = {
    "part_number": ("part_number", "part_number"),
    "drawing_number": ("drawing_number", "drawing_number"),
    "revision": ("revision", "revision"),
    "customer": ("customer_name", "customer_oem"),
    "supplier": ("supplier_name", "supplier_name"),
    "process": ("process_name", "manufacturing_process"),
    "material": ("material", "material"),
}

FIELD_PRIORITY = {
    "part_number": [
        DocumentType.DESIGN_RECORD,
        DocumentType.BALLOONED_DRAWING,
        DocumentType.FAIR,
        DocumentType.PSW,
        DocumentType.DIMENSIONAL_RESULTS,
    ],
    "drawing_number": [
        DocumentType.DESIGN_RECORD,
        DocumentType.BALLOONED_DRAWING,
        DocumentType.FAIR,
        DocumentType.PSW,
    ],
    "revision": [
        DocumentType.DESIGN_RECORD,
        DocumentType.BALLOONED_DRAWING,
        DocumentType.FAIR,
        DocumentType.PSW,
        DocumentType.CONTROL_PLAN,
        DocumentType.PFMEA,
        DocumentType.PROCESS_FLOW,
    ],
    "customer": [
        DocumentType.PSW,
        DocumentType.FAIR,
        DocumentType.CONTROL_PLAN,
        DocumentType.PFMEA,
    ],
    "supplier": [
        DocumentType.PSW,
        DocumentType.FAIR,
        DocumentType.CONTROL_PLAN,
        DocumentType.PFMEA,
    ],
    "process": [
        DocumentType.PROCESS_FLOW,
        DocumentType.PFMEA,
        DocumentType.CONTROL_PLAN,
    ],
    "material": [
        DocumentType.DESIGN_RECORD,
        DocumentType.MATERIAL_RESULTS,
        DocumentType.MATERIAL_CERTIFICATE,
        DocumentType.FAIR,
    ],
}


def normalize_value(value: str) -> str:
    return " ".join(value.strip().upper().split())


class CrossDocumentValidator:
    def evaluate(
        self, package: SubmissionPackage
    ) -> tuple[MetadataMasterRecord, list[ValidationFinding]]:
        master_record = MetadataMasterRecord()
        conflicts: list[ValidationFinding] = []

        for field_name, (document_key, context_key) in FIELD_KEY_MAP.items():
            selected_value, field_conflicts = self._resolve_field(
                package.documents,
                package.context,
                field_name,
                document_key,
                context_key,
            )
            setattr(master_record, field_name, selected_value)
            conflicts.extend(field_conflicts)

        return master_record, conflicts

    def _resolve_field(
        self,
        documents: list[DocumentRecord],
        context: SubmissionContext,
        field_name: str,
        document_key: str,
        context_key: str,
    ) -> tuple[str, list[ValidationFinding]]:
        observations: list[tuple[str, DocumentRecord, EvidenceRef, float]] = []
        for document in documents:
            extracted = document.get_field(document_key)
            if not extracted.is_present:
                continue
            value = extracted.text.strip()
            if not value:
                continue
            evidence = (
                extracted.evidence[0]
                if extracted.evidence
                else EvidenceRef(
                    file_name=document.file_name,
                    field_name=document_key,
                    snippet=value,
                    confidence=extracted.confidence,
                )
            )
            confidence = extracted.confidence
            if extracted.status in {
                ExtractionStatus.INFERRED_LOW_CONFIDENCE,
                ExtractionStatus.REQUIRES_MANUAL_REVIEW,
            }:
                confidence = min(confidence, 0.6)
            observations.append((value, document, evidence, confidence))

        if not observations:
            context_value = getattr(context, context_key, None)
            return (str(context_value).strip() if context_value else "", [])

        counts = Counter(normalize_value(value) for value, _, _, _ in observations)
        if len(counts) == 1:
            return observations[0][0], []

        winner = self._select_authoritative_value(field_name, observations)
        evidence = [entry[2] for entry in observations[:6]]
        related_documents = [entry[1].document_type for entry in observations]
        severity = (
            Severity.CRITICAL
            if field_name in {"part_number", "drawing_number", "revision"}
            else Severity.MAJOR
        )
        blocking = field_name in {"part_number", "drawing_number", "revision"}
        values_text = "; ".join(f"{document.file_name}={value}" for value, document, _, _ in observations)
        description = (
            f"{field_name.replace('_', ' ').title()} is inconsistent across mandatory records. "
            f"Observed values: {values_text}. Selected master value: {winner}."
        )
        finding = ValidationFinding(
            finding_id=f"conflict-{field_name}",
            category="cross_document_consistency",
            severity=severity,
            title=f"{field_name.replace('_', ' ').title()} mismatch across documents",
            description=description,
            blocking=blocking,
            evidence=evidence,
            related_documents=related_documents,
            confidence=min(entry[3] for entry in observations),
            suggested_action=(
                f"Resolve the {field_name.replace('_', ' ')} mismatch and update all affected documents to the same released value."
            ),
        )
        return winner, [finding]

    def _select_authoritative_value(
        self,
        field_name: str,
        observations: list[tuple[str, DocumentRecord, EvidenceRef, float]],
    ) -> str:
        priority = FIELD_PRIORITY[field_name]
        for preferred_type in priority:
            for value, document, _, _ in observations:
                if document.document_type == preferred_type:
                    return value

        counts = Counter(normalize_value(entry[0]) for entry in observations)
        ranked = sorted(
            observations,
            key=lambda item: (counts[normalize_value(item[0])], item[3]),
            reverse=True,
        )
        return ranked[0][0]

