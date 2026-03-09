from ppapcheck.models import DocumentType, MeasurementStatus
from ppapcheck.services.upload_submission_builder import TableSection, TextFragment, UploadSubmissionBuilder


def test_classify_vda_cover_sheet_as_psw():
    builder = UploadSubmissionBuilder()
    fragment = TextFragment(
        text=(
            "Cover sheet PPA report\n"
            "Report on production process and product approval (PPA)\n"
            "Organization Mita Kalip ve Dokum San. A.S.\n"
        ),
        page_number=1,
    )

    document_type, confidence, label = builder._classify_pdf_page("bundle.pdf", fragment)

    assert document_type == DocumentType.PSW
    assert confidence >= 0.95
    assert "PPA" in label


def test_classify_vda_dimensional_page_as_dimensional_results():
    builder = UploadSubmissionBuilder()
    fragment = TextFragment(
        text=(
            "Product-related deliverables\n"
            "No. Requirements / Specification Actual values of organization Specification met\n"
            "101 20 -0,1 19,96 19,98\n"
            "102 15,40 +0,05 Gauge Gauge\n"
        ),
        page_number=4,
    )

    document_type, confidence, _ = builder._classify_pdf_page("bundle.pdf", fragment)

    assert document_type == DocumentType.DIMENSIONAL_RESULTS
    assert confidence >= 0.95


def test_classify_vda_material_page_as_material_results():
    builder = UploadSubmissionBuilder()
    fragment = TextFragment(
        text=(
            "Product-related deliverables\n"
            "Chemical Composition (%)\n"
            "TS EN 1706\n"
            "Hardness: min 90 HB 98\n"
        ),
        page_number=10,
    )

    document_type, confidence, _ = builder._classify_pdf_page("bundle.pdf", fragment)

    assert document_type == DocumentType.MATERIAL_RESULTS
    assert confidence >= 0.95


def test_table_hint_reclassifies_vda_material_page_even_when_text_looks_like_design_record():
    builder = UploadSubmissionBuilder()
    fragments = [
        TextFragment(
            text=(
                "Product-related Report 26011 deliverables\n"
                "Organization Mita Kalip ve Dokum San. A.S.\n"
                "Part Number U.32.100.771 Hardware version - Part Number A 205 257 03 00\n"
                "Drawing number A 205 257 03 00 Software version - Drawing number A 205 257 03 00\n"
            ),
            page_number=12,
        )
    ]
    filler_rows = [["", "", "", "", "", "", "", "", "", "", "", ""] for _ in range(17)]
    material_table = TableSection(
        section_name="pdf_page_12_table_1",
        rows=[
            *filler_rows,
            ["No.", "", "", "Requirements / Specification", "", "", "Actual values of organization", "", "", "", "", ""],
            ["", "", "", "TS EN 12163", "", "", "", "", "", "", "", ""],
            ["", "", "", "CuAl10Ni5Fe4 Al. Bronze", "", "", "", "", "", "", "", ""],
            ["", "", "", "Supplier Batch No", "", "", "250993C091", "", "", "", "", ""],
            ["", "", "", "Chemical Composition (%)", "", "", "", "", "", "", "", ""],
        ],
    )

    sections = builder._build_pdf_sections("bundle.pdf", fragments, [material_table])

    assert len(sections) == 1
    assert sections[0].document_type == DocumentType.MATERIAL_RESULTS
    assert sections[0].classification_confidence >= 0.95


def test_extract_vda_dimensional_rows_with_deep_header_and_numeric_evaluation():
    builder = UploadSubmissionBuilder()
    filler_rows = [["", "", "", "", "", "", "", "", "", "", "", ""] for _ in range(17)]
    dimensional_table = TableSection(
        section_name="pdf_page_4_table_1",
        rows=[
            *filler_rows,
            ["No.", "", "", "Requirements / Specification", "", "", "Actual values of organization", "", "", "", "", ""],
            ["", "", "", "", "", "", "581", "", "", "", "582", ""],
            ["101", "", "", "20 -0,1", "", "", "19,96", "", "", "", "20,05", ""],
            ["102", "", "", "15,40 +0,05", "", "", "Gauge", "", "", "", "15,43", ""],
        ],
    )

    structured = builder._extract_structured_rows(
        "bundle.pdf",
        DocumentType.DIMENSIONAL_RESULTS,
        [dimensional_table],
    )

    assert len(structured["drawing_characteristics"]) == 2
    assert len(structured["inspection_results"]) == 4
    assert structured["drawing_characteristics"][0].characteristic_id == "101"
    assert structured["inspection_results"][0].result == MeasurementStatus.PASS
    assert structured["inspection_results"][1].result == MeasurementStatus.FAIL
    assert structured["inspection_results"][2].result == MeasurementStatus.UNCLEAR


def test_degree_minute_second_tolerances_remain_unclear_until_specialized_parser_exists():
    builder = UploadSubmissionBuilder()

    status = builder._evaluate_vda_measurement('16°±0"30\'', "16,047")
    nominal, tolerance, unit = builder._derive_spec_fields('16°±0"30\'')

    assert status == MeasurementStatus.UNCLEAR
    assert nominal == "16.0"
    assert tolerance is None
    assert unit == "deg"


def test_extract_metadata_prefers_real_package_values():
    builder = UploadSubmissionBuilder()
    fragments = [
        TextFragment(
            text=(
                "Cover sheet PPA report\n"
                "Organization Mita Kalip ve Dokum San. A.S.\n"
                "Part Number U.32.100.771 Hardware version - Part Number A 205 257 03 00\n"
                "Drawing number A 205 257 03 00 Software version - Drawing number A 205 257 03 00\n"
                "Version / Date 002 / 02.05.2019\n"
                "Customer decision\n"
                "Customer-ready/Ready for series production Not customer-ready/ Not ready for series production\n"
            ),
            page_number=1,
        ),
        TextFragment(
            text=(
                "Product-related deliverables\n"
                "Report number IN-26-006 Delivery note number - Customer Daimler TruckReport version 0\n"
                "Part Number U.32.100.771 Hardware version - Part Number A 205 257 03 00\n"
                "Drawing number A 205 257 03 00 Software version - Drawing number A 205 257 03 00\n"
                "Version / Date 002 / 02.05.2019\n"
            ),
            page_number=4,
        ),
    ]

    metadata = builder._extract_metadata("bundle.pdf", fragments)

    assert metadata["part_number"].text == "U.32.100.771"
    assert metadata["drawing_number"].text == "A 205 257 03 00"
    assert metadata["revision"].text == "002"
    assert metadata["customer_name"].text == "Daimler Truck"
    assert metadata["supplier_name"].text == "Mita Kalip ve Dokum San. A.S."
