from __future__ import annotations

from statistics import mean

from ppapcheck.models import (
    ConfidenceLevel,
    Decision,
    Severity,
    ValidationFinding,
)


SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 28,
    Severity.MAJOR: 14,
    Severity.MINOR: 6,
    Severity.OBSERVATION: 2,
}


class ScoringEngine:
    def score(
        self,
        findings: list[ValidationFinding],
        manual_review_flags: list[ValidationFinding],
    ) -> tuple[int, Decision, ConfidenceLevel]:
        severity_penalty = sum(SEVERITY_WEIGHTS[finding.severity] for finding in findings)
        score = max(0, 100 - severity_penalty - (4 * len(manual_review_flags)))

        critical_count = sum(1 for finding in findings if finding.severity == Severity.CRITICAL)
        major_count = sum(1 for finding in findings if finding.severity == Severity.MAJOR)
        blocking = any(finding.blocking for finding in findings) or critical_count > 0
        if blocking:
            decision = Decision.BLOCK_SUBMISSION
        elif major_count >= 3 or score < 60:
            decision = Decision.FAIL
        elif manual_review_flags or major_count > 0:
            decision = Decision.CONDITIONAL
        elif findings:
            decision = Decision.PASS_WITH_OBSERVATIONS
        else:
            decision = Decision.PASS

        confidence = self._confidence_level(findings, manual_review_flags)
        return score, decision, confidence

    def _confidence_level(
        self,
        findings: list[ValidationFinding],
        manual_review_flags: list[ValidationFinding],
    ) -> ConfidenceLevel:
        confidences = [finding.confidence for finding in findings + manual_review_flags if finding.confidence]
        average_confidence = mean(confidences) if confidences else 0.92
        if manual_review_flags or average_confidence < 0.72:
            return ConfidenceLevel.LOW
        if average_confidence < 0.88:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.HIGH

