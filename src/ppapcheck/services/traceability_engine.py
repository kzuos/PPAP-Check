from __future__ import annotations

from ppapcheck.models import (
    CharacteristicType,
    CheckResult,
    CheckStatus,
    DocumentType,
    Severity,
    SubmissionMode,
    SubmissionPackage,
    ValidationFinding,
)


class TraceabilityEngine:
    def evaluate(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> tuple[list[CheckResult], list[ValidationFinding]]:
        checks: list[CheckResult] = []
        findings: list[ValidationFinding] = []

        checks.extend(self._drawing_to_results_checks(package, mode, findings))
        checks.extend(self._process_chain_checks(package, findings))
        if mode in {SubmissionMode.PPAP, SubmissionMode.HYBRID}:
            checks.extend(self._special_characteristic_checks(package, mode, findings))

        return checks, findings

    def _drawing_to_results_checks(
        self,
        package: SubmissionPackage,
        mode: SubmissionMode,
        findings: list[ValidationFinding],
    ) -> list[CheckResult]:
        drawing_characteristics = [
            characteristic
            for document in package.documents
            if document.document_type in {DocumentType.DESIGN_RECORD, DocumentType.BALLOONED_DRAWING}
            for characteristic in document.drawing_characteristics
        ]
        inspection_results = [
            result
            for document in package.documents
            if document.document_type in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}
            for result in document.inspection_results
        ]

        if not drawing_characteristics:
            if inspection_results:
                evidence = [result.evidence[0] for result in inspection_results if result.evidence][:6]
                identifiers: list[str] = []
                for result in inspection_results:
                    identifier = result.balloon_number or result.characteristic_id or result.source_document
                    if identifier in identifiers:
                        continue
                    identifiers.append(identifier)
                    if len(identifiers) >= 12:
                        break
                severity = Severity.CRITICAL if mode in {SubmissionMode.FAI, SubmissionMode.HYBRID} else Severity.MAJOR
                findings.append(
                    ValidationFinding(
                        finding_id="trace-results-without-drawing",
                        category="traceability",
                        severity=severity,
                        title="Measured features cannot be traced to a released drawing",
                        description=(
                            "Inspection results were extracted, but no released drawing or ballooned drawing characteristics were available "
                            "to confirm characteristic identity and configuration control. "
                            f"Measured items without verified drawing linkage include: {', '.join(identifiers)}."
                        ),
                        blocking=severity == Severity.CRITICAL,
                        evidence=evidence,
                        related_documents=[
                            DocumentType.DESIGN_RECORD,
                            DocumentType.BALLOONED_DRAWING,
                            DocumentType.DIMENSIONAL_RESULTS,
                            DocumentType.FAIR,
                        ],
                        related_characteristics=identifiers,
                        suggested_action="Provide the released drawing or ballooned drawing and align the measured rows to approved characteristic identifiers.",
                    )
                )
                return [
                    CheckResult(
                        check_id="trace-drawing-missing",
                        name="Drawing to results traceability",
                        status=CheckStatus.FAIL,
                        severity=severity,
                        description="Measured results exist, but no released drawing evidence was available to verify characteristic traceability.",
                        evidence=evidence,
                        confidence=0.9,
                        suggested_action="Attach the released drawing or ballooned drawing used to create the dimensional or FAIR results.",
                    )
                ]
            return [
                CheckResult(
                    check_id="trace-drawing-missing",
                    name="Drawing to results traceability",
                    status=CheckStatus.UNCLEAR,
                    severity=Severity.MAJOR,
                    description="No drawing characteristics were extracted, so dimensional traceability could not be verified.",
                    confidence=0.45,
                    suggested_action="Provide a released drawing or ballooned drawing with characteristic identifiers.",
                )
            ]

        lookup = {
            (result.characteristic_id or "", result.balloon_number or ""): result
            for result in inspection_results
        }
        missing_characteristics = []
        failed_characteristics = []
        for characteristic in drawing_characteristics:
            key = (characteristic.characteristic_id or "", characteristic.balloon_number or "")
            if key not in lookup:
                missing_characteristics.append(characteristic)
                continue
            if lookup[key].result.value == "fail":
                failed_characteristics.append(characteristic)

        checks: list[CheckResult] = []
        if missing_characteristics:
            severity = (
                Severity.CRITICAL
                if mode in {SubmissionMode.FAI, SubmissionMode.HYBRID}
                or any(
                    characteristic.characteristic_type
                    in {CharacteristicType.SPECIAL, CharacteristicType.CRITICAL}
                    for characteristic in missing_characteristics
                )
                else Severity.MAJOR
            )
            blocking = severity == Severity.CRITICAL
            identifiers = [
                characteristic.balloon_number or characteristic.characteristic_id
                for characteristic in missing_characteristics
            ]
            evidence = [item.evidence[0] for item in missing_characteristics if item.evidence][:6]
            findings.append(
                ValidationFinding(
                    finding_id="trace-missing-accountability",
                    category="traceability",
                    severity=severity,
                    title="Incomplete characteristic accountability",
                    description=(
                        "The drawing contains characteristics without corresponding inspection evidence. "
                        f"Missing accountability for: {', '.join(identifiers)}."
                    ),
                    blocking=blocking,
                    evidence=evidence,
                    related_documents=[
                        DocumentType.DESIGN_RECORD,
                        DocumentType.BALLOONED_DRAWING,
                        DocumentType.DIMENSIONAL_RESULTS,
                        DocumentType.FAIR,
                    ],
                    related_characteristics=identifiers,
                    suggested_action="Update the dimensional results or FAIR to include every ballooned or identified drawing characteristic.",
                )
            )
            checks.append(
                CheckResult(
                    check_id="trace-drawing-to-results",
                    name="Drawing to results traceability",
                    status=CheckStatus.FAIL,
                    severity=severity,
                    description=f"Missing inspection accountability for {', '.join(identifiers)}.",
                    evidence=evidence,
                    confidence=0.95,
                    suggested_action="Add measured results for every listed characteristic and reissue the affected inspection documents.",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="trace-drawing-to-results",
                    name="Drawing to results traceability",
                    status=CheckStatus.PASS,
                    description="Every extracted drawing characteristic has matching inspection evidence.",
                    confidence=0.92,
                )
            )

        if failed_characteristics:
            identifiers = [
                characteristic.balloon_number or characteristic.characteristic_id
                for characteristic in failed_characteristics
            ]
            evidence = [item.evidence[0] for item in failed_characteristics if item.evidence][:6]
            findings.append(
                ValidationFinding(
                    finding_id="trace-failed-measurements",
                    category="traceability",
                    severity=Severity.MAJOR,
                    title="Inspection results contain rejected characteristics",
                    description=f"The inspection evidence includes failing results for characteristics {', '.join(identifiers)}.",
                    evidence=evidence,
                    related_documents=[DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR],
                    related_characteristics=identifiers,
                    suggested_action="Resolve the nonconforming measurements and document disposition before submission.",
                )
            )

        return checks

    def _process_chain_checks(
        self, package: SubmissionPackage, findings: list[ValidationFinding]
    ) -> list[CheckResult]:
        flow_steps = [
            step
            for document in package.documents
            if document.document_type == DocumentType.PROCESS_FLOW
            for step in document.process_flow_steps
        ]
        pfmea_steps = {
            entry.step_id
            for document in package.documents
            if document.document_type == DocumentType.PFMEA
            for entry in document.pfmea_entries
        }
        control_steps = {
            entry.step_id
            for document in package.documents
            if document.document_type == DocumentType.CONTROL_PLAN
            for entry in document.control_plan_entries
        }

        if not flow_steps:
            return []

        missing_in_pfmea = [step.step_id for step in flow_steps if step.step_id not in pfmea_steps]
        missing_in_control = [step.step_id for step in flow_steps if step.step_id not in control_steps]
        checks: list[CheckResult] = []

        if missing_in_pfmea or missing_in_control:
            issues = []
            if missing_in_pfmea:
                issues.append(f"missing in PFMEA: {', '.join(missing_in_pfmea)}")
            if missing_in_control:
                issues.append(f"missing in Control Plan: {', '.join(missing_in_control)}")
            description = "Process flow linkage is incomplete; " + "; ".join(issues) + "."
            evidence = [
                step.evidence[0]
                for step in flow_steps
                if step.step_id in set(missing_in_pfmea + missing_in_control) and step.evidence
            ][:6]
            findings.append(
                ValidationFinding(
                    finding_id="trace-process-chain",
                    category="traceability",
                    severity=Severity.MAJOR,
                    title="Process flow is not fully linked to PFMEA and Control Plan",
                    description=description,
                    evidence=evidence,
                    related_documents=[DocumentType.PROCESS_FLOW, DocumentType.PFMEA, DocumentType.CONTROL_PLAN],
                    suggested_action="Align process flow steps with PFMEA and Control Plan step identifiers and sequencing.",
                )
            )
            checks.append(
                CheckResult(
                    check_id="trace-process-chain",
                    name="Process flow to PFMEA to Control Plan linkage",
                    status=CheckStatus.FAIL,
                    severity=Severity.MAJOR,
                    description=description,
                    evidence=evidence,
                    confidence=0.93,
                    suggested_action="Update PFMEA and Control Plan so every process flow step is represented consistently.",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check_id="trace-process-chain",
                    name="Process flow to PFMEA to Control Plan linkage",
                    status=CheckStatus.PASS,
                    description="Each extracted process flow step is represented in both PFMEA and Control Plan evidence.",
                    confidence=0.9,
                )
            )

        return checks

    def _special_characteristic_checks(
        self,
        package: SubmissionPackage,
        mode: SubmissionMode,
        findings: list[ValidationFinding],
    ) -> list[CheckResult]:
        special_characteristics = [
            characteristic
            for document in package.documents
            if document.document_type in {DocumentType.DESIGN_RECORD, DocumentType.BALLOONED_DRAWING}
            for characteristic in document.drawing_characteristics
            if characteristic.characteristic_type in {CharacteristicType.SPECIAL, CharacteristicType.CRITICAL}
        ]
        if not special_characteristics:
            return []

        control_entries = [
            entry
            for document in package.documents
            if document.document_type == DocumentType.CONTROL_PLAN
            for entry in document.control_plan_entries
        ]
        covered_ids = {characteristic_id for entry in control_entries for characteristic_id in entry.characteristic_ids}
        uncovered = [
            characteristic
            for characteristic in special_characteristics
            if characteristic.characteristic_id not in covered_ids
        ]
        if not uncovered:
            return [
                CheckResult(
                    check_id="trace-special-characteristics",
                    name="Special characteristic control linkage",
                    status=CheckStatus.PASS,
                    description="Every extracted special or critical characteristic is represented in the Control Plan.",
                    confidence=0.91,
                )
            ]

        identifiers = [item.balloon_number or item.characteristic_id for item in uncovered]
        evidence = [item.evidence[0] for item in uncovered if item.evidence][:6]
        severity = Severity.CRITICAL if mode in {SubmissionMode.FAI, SubmissionMode.HYBRID} else Severity.MAJOR
        findings.append(
            ValidationFinding(
                finding_id="trace-special-characteristics",
                category="traceability",
                severity=severity,
                title="Special characteristic linkage is broken",
                description=(
                    "Special or critical characteristics are not represented in the Control Plan. "
                    f"Missing control linkage for: {', '.join(identifiers)}."
                ),
                blocking=severity == Severity.CRITICAL,
                evidence=evidence,
                related_documents=[DocumentType.CONTROL_PLAN, DocumentType.DESIGN_RECORD, DocumentType.BALLOONED_DRAWING],
                related_characteristics=identifiers,
                suggested_action="Revise the Control Plan to include each listed special characteristic and define a specific control method and reaction plan.",
            )
        )
        return [
            CheckResult(
                check_id="trace-special-characteristics",
                name="Special characteristic control linkage",
                status=CheckStatus.FAIL,
                severity=severity,
                description=f"Special characteristic control is missing for {', '.join(identifiers)}.",
                evidence=evidence,
                confidence=0.95,
                suggested_action="Add the missing special characteristic controls and reissue the Control Plan.",
            )
        ]
