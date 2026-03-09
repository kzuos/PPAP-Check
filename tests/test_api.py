from fastapi.testclient import TestClient

from ppapcheck.main import app


client = TestClient(app)


def test_sample_report_endpoint_returns_blocked_result():
    response = client.get("/api/samples/hybrid_blocked")

    assert response.status_code == 200
    body = response.json()
    assert body["overall_decision"] == "BLOCK_SUBMISSION"
    assert body["submission_mode"] == "HYBRID"


def test_dashboard_renders():
    response = client.get("/")

    assert response.status_code == 200
    assert "Submission Readiness Review" in response.text
    assert "Machine-Readable Output" in response.text


def test_validate_upload_endpoint_accepts_text_documents():
    files = [
        (
            "files",
            (
                "demo_psw.txt",
                (
                    "Part Submission Warrant\n"
                    "Part Number: ABC-123\n"
                    "Drawing Number: DWG-123\n"
                    "Revision: A\n"
                    "Customer: Ford\n"
                    "Supplier: Demo Supplier\n"
                    "Submission Reason: Initial submission\n"
                    "Approval Status: Submitted\n"
                    "Signatory: Jane Doe\n"
                    "Date: 2026-03-01\n"
                ).encode("utf-8"),
                "text/plain",
            ),
        ),
        (
            "files",
            (
                "demo_design_record.txt",
                (
                    "Design Record\n"
                    "Part Number: ABC-123\n"
                    "Drawing Number: DWG-123\n"
                    "Revision: A\n"
                    "Material: Steel 1018\n"
                ).encode("utf-8"),
                "text/plain",
            ),
        ),
    ]
    data = {
        "requested_submission_mode": "PPAP",
        "ppap_level": "1",
        "customer_oem": "Ford",
        "supplier_name": "Demo Supplier",
    }

    response = client.post("/api/validate-upload", files=files, data=data)

    assert response.status_code == 200
    body = response.json()
    assert body["report"]["submission_mode"] == "PPAP"
    assert body["report"]["metadata_master_record"]["part_number"] == "ABC-123"
    assert body["report"]["missing_documents"] == []
    assert len(body["report"]["document_inventory"]) == 2


def test_upload_dashboard_renders_uploaded_result():
    files = [
        (
            "files",
            (
                "demo_psw.txt",
                (
                    "Part Submission Warrant\n"
                    "Part Number: ZX-900\n"
                    "Drawing Number: ZX-DWG\n"
                    "Revision: C\n"
                    "Customer: GM\n"
                    "Supplier: Atlas Parts\n"
                    "Submission Reason: Tool transfer\n"
                    "Approval Status: Pending\n"
                    "Signatory: Omar Yilmaz\n"
                    "Date: 2026-03-02\n"
                ).encode("utf-8"),
                "text/plain",
            ),
        )
    ]
    data = {
        "requested_submission_mode": "PPAP",
        "ppap_level": "1",
    }

    response = client.post("/", files=files, data=data)

    assert response.status_code == 200
    assert "demo_psw.txt" in response.text
    assert "UPLOAD" in response.text
