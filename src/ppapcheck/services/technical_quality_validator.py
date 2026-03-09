from __future__ import annotations

import re

from ppapcheck.models import (
    CharacteristicType,
    DocumentType,
    MeasurementSummary,
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
        findings.extend(self._check_out_of_tolerance_results(package))
        findings.extend(self._check_measurement_context(package))
        findings.extend(self._check_measurement_evaluability(package))
        findings.extend(self._check_material_evidence_traceability(package))
        findings.extend(self._check_pfmea_to_control_plan(package))

        return findings

    def summarize_measurements(self, package: SubmissionPackage) -> MeasurementSummary:
        source_documents = [
            document
            for document in package.documents
            if document.document_type in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}
        ]
        results = [
            result
            for document in source_documents
            for result in document.inspection_results
        ]
        characteristic_ids = {
            characteristic.characteristic_id
            for document in source_documents
            for characteristic in document.drawing_characteristics
            if characteristic.characteristic_id
        }
        characteristic_ids.update(
            result.characteristic_id
            for result in results
            if result.characteristic_id
        )
        return MeasurementSummary(
            total_characteristics=len(characteristic_ids),
            total_results=len(results),
            passed_results=sum(1 for result in results if result.result.value == "pass"),
            failed_results=sum(1 for result in results if result.result.value == "fail"),
            unclear_results=sum(1 for result in results if result.result.value == "unclear"),
            numeric_results=sum(
                1 for result in results if self._parse_numeric_value(result.measured_value) is not None
            ),
            attribute_results=sum(
                1
                for result in results
                if result.measured_value and self._parse_numeric_value(result.measured_value) is None
            ),
            source_documents=[document.file_name for document in source_documents],
        )

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
        characteristics_by_document: dict[str, set[str]] = {
            document.file_name: {characteristic.characteristic_id for characteristic in document.drawing_characteristics}
            for document in package.documents
        }
        for document in package.documents:
            if document.document_type not in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}:
                continue
            for result in document.inspection_results:
                if result.characteristic_id and result.characteristic_id in characteristics_by_document.get(document.file_name, set()):
                    continue
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

    def _check_out_of_tolerance_results(self, package: SubmissionPackage) -> list[ValidationFinding]:
        failed_results = [
            result
            for document in package.documents
            if document.document_type in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}
            for result in document.inspection_results
            if result.result.value == "fail"
        ]
        if not failed_results:
            return []

        identifiers = [
            result.balloon_number or result.characteristic_id or result.source_document
            for result in failed_results[:12]
        ]
        evidence = [result.evidence[0] for result in failed_results if result.evidence][:6]
        return [
            ValidationFinding(
                finding_id="tech-out-of-tolerance-results",
                category="technical_quality",
                severity=Severity.CRITICAL,
                title="Measured results exceed extracted tolerance limits",
                description=(
                    "One or more measured characteristics appear out of tolerance based on the extracted report specification. "
                    f"Affected characteristics: {', '.join(identifiers)}."
                ),
                blocking=True,
                evidence=evidence,
                related_documents=[DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR],
                related_characteristics=identifiers,
                suggested_action="Review the listed dimensional results against the released drawing and correct any nonconforming measurements or dispositions before submission.",
            )
        ]

    def _check_measurement_evaluability(self, package: SubmissionPackage) -> list[ValidationFinding]:
        summary = self.summarize_measurements(package)
        if summary.total_results < 15 or summary.unclear_results == 0:
            return []

        unclear_ratio = summary.unclear_results / summary.total_results
        if unclear_ratio < 0.15:
            return []

        evidence = []
        related_characteristics: list[str] = []
        for document in package.documents:
            if document.document_type not in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}:
                continue
            for result in document.inspection_results:
                if result.result.value != "unclear":
                    continue
                if result.evidence:
                    evidence.append(result.evidence[0])
                identifier = result.balloon_number or result.characteristic_id
                if identifier and identifier not in related_characteristics:
                    related_characteristics.append(identifier)
                if len(evidence) >= 6:
                    break
            if len(evidence) >= 6:
                break

        severity = Severity.MAJOR if unclear_ratio >= 0.35 and summary.total_results >= 30 else Severity.MINOR
        percent = round(unclear_ratio * 100)
        return [
            ValidationFinding(
                finding_id="tech-measurement-evaluability",
                category="technical_quality",
                severity=severity,
                title="A substantial share of measured results requires manual engineering review",
                description=(
                    f"{summary.unclear_results} of {summary.total_results} extracted measurement results ({percent}%) "
                    "could not be automatically evaluated against the extracted tolerance context. "
                    "This usually indicates attribute checks, gauge-only entries, geometric callouts, or tolerance syntax that needs visual review."
                ),
                evidence=evidence,
                related_documents=[DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR],
                related_characteristics=related_characteristics[:12],
                suggested_action="Visually review the unclear measurement rows against the native report and released drawing before using the package decision without human sign-off.",
            )
        ]

    def _check_material_evidence_traceability(self, package: SubmissionPackage) -> list[ValidationFinding]:
        material_documents = [
            document
            for document in package.documents
            if document.document_type == DocumentType.MATERIAL_RESULTS
        ]
        if not material_documents:
            return []

        if any(document.certificates for document in material_documents):
            return []

        evidence = []
        for document in material_documents:
            material_field = document.get_field("material")
            if material_field.evidence:
                evidence.append(material_field.evidence[0])
            if len(evidence) >= 4:
                break

        return [
            ValidationFinding(
                finding_id="tech-material-traceability-missing",
                category="technical_quality",
                severity=Severity.MAJOR,
                title="Material test evidence lacks identifiable batch or specification linkage",
                description=(
                    "Material results were provided, but no verifiable material specification or supplier batch reference was extracted. "
                    "Material traceability remains incomplete."
                ),
                evidence=evidence,
                related_documents=[DocumentType.MATERIAL_RESULTS, DocumentType.MATERIAL_CERTIFICATE],
                suggested_action="Attach the material certificate or update the material report so the material grade and supplier batch can be verified directly.",
            )
        ]

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

    def _parse_numeric_value(self, value: str | None) -> float | None:
        if not value:
            return None
        normalized = value.replace(",", ".")
        if "x" in normalized.lower():
            return None
        match = re.search(r"[+-]?\d+(?:\.\d+)?", normalized)
        if not match:
            return None
        return float(match.group(0))
