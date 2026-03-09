from ppapcheck.models import Decision
from ppapcheck.services.sample_submissions import get_sample_submissions
from ppapcheck.services.validation_orchestrator import ValidationOrchestrator


def test_blocked_hybrid_submission_is_blocked():
    samples = get_sample_submissions()
    report = ValidationOrchestrator().validate(samples["hybrid_blocked"])

    assert report.overall_decision == Decision.BLOCK_SUBMISSION
    assert any(finding.title == "Revision mismatch across documents" for finding in report.cross_document_conflicts)
    assert any("Incomplete characteristic accountability" == finding.title for finding in report.nonconformities)


def test_ppap_ready_submission_passes_with_observations():
    samples = get_sample_submissions()
    report = ValidationOrchestrator().validate(samples["ppap_ready_with_observations"])

    assert report.overall_decision == Decision.PASS_WITH_OBSERVATIONS
    assert not report.missing_documents
    assert any(finding.severity.value == "Observation" for finding in report.nonconformities)


def test_fai_sample_requires_manual_review():
    samples = get_sample_submissions()
    report = ValidationOrchestrator().validate(samples["fai_conditional_low_confidence"])

    assert report.overall_decision == Decision.CONDITIONAL
    assert report.manual_review_flags
    assert any(finding.title == "Measured results are missing unit context" for finding in report.technical_findings)

