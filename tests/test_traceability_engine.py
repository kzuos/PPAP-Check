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
from ppapcheck.services.traceability_engine import TraceabilityEngine


def test_results_without_released_drawing_raise_traceability_failure():
    package = SubmissionPackage(
        submission_id="pkg-2",
        submission_mode=SubmissionMode.PPAP,
        context=SubmissionContext(requested_submission_mode=SubmissionMode.PPAP, ppap_level=3),
        documents=[
            DocumentRecord(
                file_name="dimensional_results.pdf",
                document_type=DocumentType.DIMENSIONAL_RESULTS,
                inspection_results=[
                    InspectionResult(
                        characteristic_id="101",
                        balloon_number="101",
                        measured_value="19.96",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        source_document="dimensional_results.pdf",
                        evidence=[
                            EvidenceRef(
                                file_name="dimensional_results.pdf",
                                page_number=4,
                                section_name="pdf_page_4_table_1",
                                field_name="measurement",
                                snippet="101 | 20 -0,1 | 19,96",
                                confidence=0.91,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    checks, findings = TraceabilityEngine().evaluate(package, SubmissionMode.PPAP)

    assert checks[0].status.value == "fail"
    assert findings
    assert findings[0].title == "Measured features cannot be traced to a released drawing"
