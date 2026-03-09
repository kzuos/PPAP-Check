from ppapcheck.models import (
    CertificateRecord,
    DocumentRecord,
    DocumentType,
    EvidenceRef,
    SubmissionContext,
    SubmissionMode,
    SubmissionPackage,
)
from ppapcheck.services.extraction_service import ExtractionService


def test_material_metadata_is_promoted_from_certificate_records():
    package = SubmissionPackage(
        submission_id="pkg-1",
        submission_mode=SubmissionMode.PPAP,
        context=SubmissionContext(requested_submission_mode=SubmissionMode.PPAP, ppap_level=3),
        documents=[
            DocumentRecord(
                file_name="material_results.pdf",
                document_type=DocumentType.MATERIAL_RESULTS,
                certificates=[
                    CertificateRecord(
                        certificate_type="material_specification",
                        identifier="CuAl10Ni5Fe4 Al. Bronze",
                        source_document="material_results.pdf",
                        evidence=[
                            EvidenceRef(
                                file_name="material_results.pdf",
                                page_number=12,
                                section_name="pdf_page_12_table_1",
                                field_name="material_specification",
                                snippet="CuAl10Ni5Fe4 Al. Bronze",
                                confidence=0.86,
                            )
                        ],
                    ),
                    CertificateRecord(
                        certificate_type="material_specification",
                        identifier="TS EN 12163",
                        source_document="material_results.pdf",
                    ),
                ],
            )
        ],
    )

    normalized = ExtractionService().normalize(package)
    material = normalized.documents[0].get_field("material")

    assert material.is_present
    assert material.text == "CuAl10Ni5Fe4 Al. Bronze / TS EN 12163"
