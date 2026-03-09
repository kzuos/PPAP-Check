from ppapcheck.models import (
    DocumentRecord,
    DocumentType,
    EvidenceRef,
    InspectionResult,
    MeasurementStatus,
    SubmissionContext,
    SubmissionMode,
    SubmissionPackage,
)
from ppapcheck.services.technical_quality_validator import TechnicalQualityValidator


def test_out_of_tolerance_results_raise_critical_finding():
    package = SubmissionPackage(
        submission_id="upload-test",
        submission_mode=SubmissionMode.PPAP,
        context=SubmissionContext(requested_submission_mode=SubmissionMode.PPAP, ppap_level=3),
        documents=[
            DocumentRecord(
                file_name="dimensional_report.pdf",
                document_type=DocumentType.DIMENSIONAL_RESULTS,
                inspection_results=[
                    InspectionResult(
                        characteristic_id="101",
                        balloon_number="101",
                        measured_value="20.05",
                        unit="mm",
                        result=MeasurementStatus.FAIL,
                        source_document="dimensional_report.pdf",
                        evidence=[
                            EvidenceRef(
                                file_name="dimensional_report.pdf",
                                page_number=4,
                                section_name="pdf_page_4_table_1",
                                field_name="measurement",
                                snippet="101 | 20 -0,1 | 20,05",
                                confidence=0.91,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    findings = TechnicalQualityValidator().evaluate(package, SubmissionMode.PPAP)

    assert any(
        finding.title == "Measured results exceed extracted tolerance limits"
        and finding.severity.value == "Critical"
        for finding in findings
    )
