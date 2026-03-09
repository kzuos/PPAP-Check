from __future__ import annotations

from ppapcheck.models import (
    CharacteristicType,
    DocumentType,
    Severity,
    SubmissionMode,
    SubmissionPackage,
    ValidationFinding,
)


class TechnicalQualityValidator:
    def evaluate(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        findings.extend(self._check_capability_coverage(package, mode))
        findings.extend(self._check_msa_presence(package, mode))
        findings.extend(self._check_measurement_context(package))
        findings.extend(self._check_pfmea_to_control_plan(package))

        return findings

    def _check_capability_coverage(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> list[ValidationFinding]:
        if mode not in {SubmissionMode.PPAP, SubmissionMode.HYBRID}:
            return []
        critical_ids = {
            characteristic.characteristic_id
            for document in package.documents
            if document.document_type in {DocumentType.DESIGN_RECORD, DocumentType.BALLOONED_DRAWING}
            for characteristic in document.drawing_characteristics
            if characteristic.characteristic_type in {CharacteristicType.SPECIAL, CharacteristicType.CRITICAL}
        }
        if not critical_ids:
            return []

        studied_ids = {
            study.characteristic_id
            for document in package.documents
            if document.document_type == DocumentType.PROCESS_STUDY
            for study in document.capability_studies
        }
        missing = sorted(critical_ids - studied_ids)
        if not missing:
            return []

        return [
            ValidationFinding(
                finding_id="tech-capability-missing",
                category="technical_quality",
                severity=Severity.MAJOR,
                title="Capability evidence is missing for critical or special characteristics",
                description=(
                    "Critical or special characteristics were identified, but no linked capability evidence was found for "
                    f"{', '.join(missing)}."
                ),
                related_documents=[DocumentType.PROCESS_STUDY, DocumentType.DESIGN_RECORD, DocumentType.BALLOONED_DRAWING],
                related_characteristics=missing,
                suggested_action="Provide capability evidence for each listed characteristic or document why capability study is not applicable.",
            )
        ]

    def _check_msa_presence(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> list[ValidationFinding]:
        if mode not in {SubmissionMode.PPAP, SubmissionMode.HYBRID}:
            return []
        has_measurements = any(
            document.inspection_results
            for document in package.documents
            if document.document_type in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}
        )
        has_msa = any(
            document.document_type == DocumentType.MSA and document.msa_studies
            for document in package.documents
        )
        if not has_measurements or has_msa:
            return []
        return [
            ValidationFinding(
                finding_id="tech-msa-missing",
                category="technical_quality",
                severity=Severity.MAJOR,
                title="Measurement evidence exists but MSA support is absent",
                description="Inspection results were provided, but no MSA study was found to support measurement credibility.",
                related_documents=[DocumentType.MSA, DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR],
                suggested_action="Attach the relevant MSA or GRR evidence for the gages used in dimensional verification.",
            )
        ]

    def _check_measurement_context(self, package: SubmissionPackage) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        missing_units: list[str] = []
        evidence = []
        for document in package.documents:
            if document.document_type not in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}:
                continue
            for result in document.inspection_results:
                if result.measured_value and not result.unit:
                    identifier = result.balloon_number or result.characteristic_id or document.file_name
                    missing_units.append(identifier)
                    if result.evidence:
                        evidence.append(result.evidence[0])

        if missing_units:
            findings.append(
                ValidationFinding(
                    finding_id="tech-missing-units",
                    category="technical_quality",
                    severity=Severity.MAJOR,
                    title="Measured results are missing unit context",
                    description=f"Measured results were reported without units for {', '.join(missing_units)}.",
                    evidence=evidence[:6],
                    related_documents=[DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR],
                    related_characteristics=missing_units,
                    suggested_action="Update the affected inspection records so measured values include explicit units.",
                )
            )
        return findings

    def _check_pfmea_to_control_plan(self, package: SubmissionPackage) -> list[ValidationFinding]:
        pfmea_entries = [
            entry
            for document in package.documents
            if document.document_type == DocumentType.PFMEA
            for entry in document.pfmea_entries
        ]
        control_entries = [
            entry
            for document in package.documents
            if document.document_type == DocumentType.CONTROL_PLAN
            for entry in document.control_plan_entries
        ]
        unmatched = []
        for entry in pfmea_entries:
            if (entry.risk_priority or 0) < 100 and (entry.severity_rating or 0) < 8 and not entry.special_characteristic_ids:
                continue
            match = any(
                control.step_id == entry.step_id
                and (
                    not entry.special_characteristic_ids
                    or set(entry.special_characteristic_ids).intersection(control.characteristic_ids)
                )
                for control in control_entries
            )
            if not match:
                unmatched.append(entry)

        if not unmatched:
            return []

        identifiers = [entry.step_id for entry in unmatched]
        evidence = [entry.evidence[0] for entry in unmatched if entry.evidence][:6]
        return [
            ValidationFinding(
                finding_id="tech-pfmea-control-plan-gap",
                category="technical_quality",
                severity=Severity.MAJOR,
                title="PFMEA high-risk items are not reflected in the Control Plan",
                description=(
                    "One or more high-risk PFMEA rows are not linked to a matching Control Plan entry. "
                    f"Affected steps: {', '.join(identifiers)}."
                ),
                evidence=evidence,
                related_documents=[DocumentType.PFMEA, DocumentType.CONTROL_PLAN],
                suggested_action="Update the Control Plan so each high-risk PFMEA row is linked to a control method and reaction plan.",
            )
        ]

