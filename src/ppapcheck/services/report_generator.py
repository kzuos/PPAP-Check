from __future__ import annotations

from ppapcheck.models import (
    Decision,
    Severity,
    ValidationFinding,
    ValidationReport,
)


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.MAJOR: 1,
    Severity.MINOR: 2,
    Severity.OBSERVATION: 3,
}


class ReportGenerator:
    def generate_expert_report(self, report: ValidationReport) -> str:
        highest_risk = sorted(report.nonconformities, key=lambda item: SEVERITY_ORDER[item.severity])[:5]
        highest_risk_lines = [
            f"- [{finding.severity}] {finding.title}: {finding.description}"
            for finding in highest_risk
        ] or ["- No major nonconformities were verified in the current evidence set."]
        measurement_summary_lines = (
            [
                f"- Extracted characteristics: {report.measurement_summary.total_characteristics}",
                f"- Extracted measurement results: {report.measurement_summary.total_results}",
                f"- Passed results: {report.measurement_summary.passed_results}",
                f"- Failed results: {report.measurement_summary.failed_results}",
                f"- Unclear results: {report.measurement_summary.unclear_results}",
                f"- Attribute or non-numeric rows: {report.measurement_summary.attribute_results}",
            ]
            if report.measurement_summary.total_results
            else ["- No dimensional or FAIR measurement rows were extracted in the current evidence set."]
        )

        missing_lines = (
            [f"- {document}" for document in report.missing_documents]
            if report.missing_documents
            else ["- No required documents were verified as missing."]
        )
        conflict_lines = (
            [f"- {finding.title}: {finding.description}" for finding in report.cross_document_conflicts]
            if report.cross_document_conflicts
            else ["- No cross-document conflicts were verified."]
        )
        traceability_lines = (
            [f"- {check.name}: {check.description}" for check in report.traceability_checks if check.status != "pass"]
            or ["- Traceability checks passed for the extracted evidence set."]
        )
        technical_lines = (
            [f"- {finding.title}: {finding.description}" for finding in report.technical_findings]
            if report.technical_findings
            else ["- No additional technical validity concerns were verified beyond the core nonconformities."]
        )
        manual_lines = (
            [f"- {finding.title}: {finding.description}" for finding in report.manual_review_flags]
            if report.manual_review_flags
            else ["- No manual review flags were raised from extraction confidence."]
        )
        action_lines = (
            [f"- {action}" for action in report.recommended_actions]
            if report.recommended_actions
            else ["- No corrective actions were generated."]
        )

        readiness = {
            Decision.PASS: "Submission can proceed based on the verified evidence.",
            Decision.PASS_WITH_OBSERVATIONS: "Submission can proceed, but minor evidence improvements are recommended.",
            Decision.CONDITIONAL: "Submission should not proceed without manual review of the flagged gaps.",
            Decision.FAIL: "Submission is not ready; substantial corrections are required before resubmission.",
            Decision.BLOCK_SUBMISSION: "Submission must be blocked until the critical issues listed below are resolved.",
        }[report.overall_decision]

        sections = [
            "# Executive Summary",
            f"Submission mode: {report.submission_mode}",
            f"Decision: {report.overall_decision}",
            f"Confidence: {report.confidence}",
            "",
            "# Submission Readiness Decision",
            readiness,
            "",
            "# Highest-Risk Findings",
            *highest_risk_lines,
            "",
            "# Missing Documents",
            *missing_lines,
            "",
            "# Measurement Evidence Summary",
            *measurement_summary_lines,
            "",
            "# Cross-Document Mismatches",
            *conflict_lines,
            "",
            "# Traceability Issues",
            *traceability_lines,
            "",
            "# Technical Validity Concerns",
            *technical_lines,
            "",
            "# Manual Review Recommendations",
            *manual_lines,
            "",
            "# Corrective Actions Required Before Resubmission",
            *action_lines,
        ]
        return "\n".join(sections)

    def collect_recommended_actions(
        self,
        findings: list[ValidationFinding],
        manual_review_flags: list[ValidationFinding],
    ) -> list[str]:
        seen: set[str] = set()
        actions: list[str] = []
        for finding in findings + manual_review_flags:
            if not finding.suggested_action:
                continue
            if finding.suggested_action in seen:
                continue
            seen.add(finding.suggested_action)
            actions.append(finding.suggested_action)
        return actions
