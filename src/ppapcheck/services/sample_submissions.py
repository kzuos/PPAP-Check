from __future__ import annotations

from ppapcheck.models import (
    CapabilityStudy,
    CharacteristicType,
    ControlPlanEntry,
    DocumentRecord,
    DocumentType,
    DrawingCharacteristic,
    EvidenceRef,
    ExtractionStatus,
    InspectionResult,
    MeasurementStatus,
    MsaStudy,
    PfmeaEntry,
    ProcessFlowStep,
    SubmissionContext,
    SubmissionMode,
    SubmissionPackage,
    CertificateRecord,
)


def ev(
    file_name: str,
    page_number: int,
    field_name: str,
    snippet: str,
    confidence: float = 0.96,
    section_name: str | None = None,
) -> EvidenceRef:
    return EvidenceRef(
        file_name=file_name,
        page_number=page_number,
        field_name=field_name,
        section_name=section_name,
        snippet=snippet,
        confidence=confidence,
    )


def get_sample_submissions() -> dict[str, SubmissionPackage]:
    return {
        "hybrid_blocked": _blocked_hybrid_submission(),
        "ppap_ready_with_observations": _ppap_ready_submission(),
        "fai_conditional_low_confidence": _conditional_fai_submission(),
    }


def _blocked_hybrid_submission() -> SubmissionPackage:
    drawing_file = "BRKT-4421_drawing_revC.pdf"
    balloon_file = "BRKT-4421_ballooned_revC.pdf"
    psw_file = "BRKT-4421_psw_revB.pdf"
    pfmea_file = "BRKT-4421_pfmea_revC.xlsx"
    flow_file = "BRKT-4421_process_flow_revC.pdf"
    control_file = "BRKT-4421_control_plan_revC.xlsx"
    dim_file = "BRKT-4421_dimensional_revC.xlsx"
    fair_file = "BRKT-4421_fair_revC.xlsx"

    return SubmissionPackage(
        submission_id="hybrid-blocked-001",
        submission_mode=SubmissionMode.HYBRID,
        context=SubmissionContext(
            customer_oem="Stellantis",
            requested_submission_mode=SubmissionMode.HYBRID,
            ppap_level=3,
            part_number="BRKT-4421",
            drawing_number="DWG-4421",
            revision="C",
            supplier_name="Anatolia Precision",
            manufacturing_process="Stamping + Zinc Nickel",
            material="HSLA 340",
            special_processes=["Zinc Nickel Plating"],
            customer_specific_rules=["CQI-11 plating evidence", "Special characteristic reaction plan required"],
        ),
        documents=[
            DocumentRecord(
                file_name=drawing_file,
                document_type=DocumentType.DESIGN_RECORD,
                metadata={
                    "part_number": {
                        "value": "BRKT-4421",
                        "evidence": [ev(drawing_file, 1, "part_number", "PART NO: BRKT-4421")],
                    },
                    "drawing_number": {
                        "value": "DWG-4421",
                        "evidence": [ev(drawing_file, 1, "drawing_number", "DRAWING NO: DWG-4421")],
                    },
                    "revision": {
                        "value": "C",
                        "evidence": [ev(drawing_file, 1, "revision", "REV C")],
                    },
                    "customer_name": {
                        "value": "Stellantis",
                        "evidence": [ev(drawing_file, 1, "customer_name", "Customer: Stellantis")],
                    },
                    "material": {
                        "value": "HSLA 340",
                        "evidence": [ev(drawing_file, 2, "material", "MATL: HSLA 340")],
                    },
                },
                drawing_characteristics=[
                    DrawingCharacteristic(
                        characteristic_id="1",
                        balloon_number="1",
                        description="Overall length",
                        nominal="125.0",
                        tolerance="+/-0.20",
                        unit="mm",
                        source_document=drawing_file,
                        evidence=[ev(drawing_file, 3, "balloon_1", "1 LENGTH 125.0 +/-0.20 mm")],
                    ),
                    DrawingCharacteristic(
                        characteristic_id="2",
                        balloon_number="2",
                        description="Material thickness",
                        nominal="2.0",
                        tolerance="+/-0.05",
                        unit="mm",
                        source_document=drawing_file,
                        evidence=[ev(drawing_file, 3, "balloon_2", "2 THICKNESS 2.0 +/-0.05 mm")],
                    ),
                    DrawingCharacteristic(
                        characteristic_id="17",
                        balloon_number="17",
                        description="Mount hole diameter",
                        nominal="8.0",
                        tolerance="+0.05/-0.00",
                        unit="mm",
                        characteristic_type=CharacteristicType.CRITICAL,
                        source_document=drawing_file,
                        evidence=[ev(drawing_file, 4, "balloon_17", "17 <SC> DIA 8.0 +0.05/-0.00")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=balloon_file,
                document_type=DocumentType.BALLOONED_DRAWING,
                metadata={
                    "part_number": {
                        "value": "BRKT-4421",
                        "evidence": [ev(balloon_file, 1, "part_number", "PART NO: BRKT-4421")],
                    },
                    "drawing_number": {
                        "value": "DWG-4421",
                        "evidence": [ev(balloon_file, 1, "drawing_number", "DRAWING NO: DWG-4421")],
                    },
                    "revision": {
                        "value": "C",
                        "evidence": [ev(balloon_file, 1, "revision", "REV C")],
                    },
                },
                drawing_characteristics=[
                    DrawingCharacteristic(
                        characteristic_id="1",
                        balloon_number="1",
                        description="Overall length",
                        nominal="125.0",
                        tolerance="+/-0.20",
                        unit="mm",
                        source_document=balloon_file,
                        evidence=[ev(balloon_file, 2, "balloon_1", "1")],
                    ),
                    DrawingCharacteristic(
                        characteristic_id="2",
                        balloon_number="2",
                        description="Material thickness",
                        nominal="2.0",
                        tolerance="+/-0.05",
                        unit="mm",
                        source_document=balloon_file,
                        evidence=[ev(balloon_file, 2, "balloon_2", "2")],
                    ),
                    DrawingCharacteristic(
                        characteristic_id="17",
                        balloon_number="17",
                        description="Mount hole diameter",
                        nominal="8.0",
                        tolerance="+0.05/-0.00",
                        unit="mm",
                        characteristic_type=CharacteristicType.CRITICAL,
                        source_document=balloon_file,
                        evidence=[ev(balloon_file, 2, "balloon_17", "17")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=psw_file,
                document_type=DocumentType.PSW,
                metadata={
                    "part_number": {
                        "value": "BRKT-4421",
                        "evidence": [ev(psw_file, 1, "part_number", "Part Number BRKT-4421")],
                    },
                    "drawing_number": {
                        "value": "DWG-4421",
                        "evidence": [ev(psw_file, 1, "drawing_number", "Drawing DWG-4421")],
                    },
                    "revision": {
                        "value": "B",
                        "evidence": [ev(psw_file, 1, "revision", "Rev B")],
                    },
                    "customer_name": {
                        "value": "Stellantis",
                        "evidence": [ev(psw_file, 1, "customer_name", "Customer Stellantis")],
                    },
                    "supplier_name": {
                        "value": "Anatolia Precision",
                        "evidence": [ev(psw_file, 1, "supplier_name", "Supplier Anatolia Precision")],
                    },
                    "submission_reason": {
                        "value": "Initial submission",
                        "evidence": [ev(psw_file, 1, "submission_reason", "Reason: Initial Submission")],
                    },
                    "approval_status": {
                        "value": "Pending",
                        "evidence": [ev(psw_file, 2, "approval_status", "Warrant Status: Pending")],
                    },
                    "signatory": {
                        "value": None,
                        "status": ExtractionStatus.NOT_FOUND,
                        "confidence": 0.0,
                    },
                    "date": {
                        "value": "2026-03-03",
                        "evidence": [ev(psw_file, 2, "date", "Submission Date 2026-03-03")],
                    },
                },
            ),
            DocumentRecord(
                file_name=pfmea_file,
                document_type=DocumentType.PFMEA,
                metadata={
                    "part_number": {"value": "BRKT-4421", "evidence": [ev(pfmea_file, 1, "part_number", "Part BRKT-4421")]},
                    "revision": {"value": "C", "evidence": [ev(pfmea_file, 1, "revision", "Rev C")]},
                    "process_name": {"value": "Stamping + Zinc Nickel", "evidence": [ev(pfmea_file, 1, "process_name", "Process: Stamping + Zinc Nickel")]},
                },
                pfmea_entries=[
                    PfmeaEntry(
                        step_id="10",
                        failure_mode="Incorrect blank length",
                        severity_rating=7,
                        risk_priority=84,
                        evidence=[ev(pfmea_file, 2, "step_10", "Step 10 Cutting")],
                    ),
                    PfmeaEntry(
                        step_id="20",
                        failure_mode="Hole diameter out of tolerance",
                        severity_rating=9,
                        risk_priority=162,
                        special_characteristic_ids=["17"],
                        evidence=[ev(pfmea_file, 3, "step_20", "Step 20 Punch critical characteristic 17")],
                    ),
                    PfmeaEntry(
                        step_id="30",
                        failure_mode="Coating thickness low",
                        severity_rating=8,
                        risk_priority=128,
                        evidence=[ev(pfmea_file, 4, "step_30", "Step 30 plating CQI-11 control")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=flow_file,
                document_type=DocumentType.PROCESS_FLOW,
                metadata={
                    "part_number": {"value": "BRKT-4421", "evidence": [ev(flow_file, 1, "part_number", "Part BRKT-4421")]},
                    "revision": {"value": "C", "evidence": [ev(flow_file, 1, "revision", "Rev C")]},
                    "process_name": {"value": "Stamping + Zinc Nickel", "evidence": [ev(flow_file, 1, "process_name", "Process: Stamping + Zinc Nickel")]},
                },
                process_flow_steps=[
                    ProcessFlowStep(step_id="10", step_name="Blank cutting", sequence=10, evidence=[ev(flow_file, 2, "step_10", "10 Blank cutting")]),
                    ProcessFlowStep(step_id="20", step_name="Punch and form", sequence=20, evidence=[ev(flow_file, 2, "step_20", "20 Punch and form")]),
                    ProcessFlowStep(step_id="30", step_name="Zinc nickel plating", sequence=30, evidence=[ev(flow_file, 2, "step_30", "30 Zinc nickel plating")]),
                ],
            ),
            DocumentRecord(
                file_name=control_file,
                document_type=DocumentType.CONTROL_PLAN,
                metadata={
                    "part_number": {"value": "BRKT-4421", "evidence": [ev(control_file, 1, "part_number", "Part BRKT-4421")]},
                    "revision": {"value": "C", "evidence": [ev(control_file, 1, "revision", "Rev C")]},
                    "process_name": {"value": "Stamping + Zinc Nickel", "evidence": [ev(control_file, 1, "process_name", "Process: Stamping + Zinc Nickel")]},
                },
                control_plan_entries=[
                    ControlPlanEntry(
                        step_id="10",
                        characteristic_ids=["1"],
                        control_method="Layout check",
                        reaction_plan="Segregate and notify supervisor",
                        sample_size=5,
                        evidence=[ev(control_file, 2, "step_10", "Step 10 characteristic 1")],
                    ),
                    ControlPlanEntry(
                        step_id="20",
                        characteristic_ids=["2"],
                        control_method="Micrometer check",
                        reaction_plan="Adjust tool and sort material",
                        sample_size=5,
                        evidence=[ev(control_file, 3, "step_20", "Step 20 characteristic 2 only")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=dim_file,
                document_type=DocumentType.DIMENSIONAL_RESULTS,
                metadata={
                    "part_number": {"value": "BRKT-4421", "evidence": [ev(dim_file, 1, "part_number", "Part BRKT-4421")]},
                    "drawing_number": {"value": "DWG-4421", "evidence": [ev(dim_file, 1, "drawing_number", "Drawing DWG-4421")]},
                    "revision": {"value": "C", "evidence": [ev(dim_file, 1, "revision", "Rev C")]},
                    "date": {"value": "2026-03-02", "evidence": [ev(dim_file, 1, "date", "Date 2026-03-02")]},
                },
                inspection_results=[
                    InspectionResult(
                        characteristic_id="1",
                        balloon_number="1",
                        measured_value="124.96",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=5,
                        source_document=dim_file,
                        evidence=[ev(dim_file, 2, "balloon_1", "1 124.96 mm PASS")],
                    ),
                    InspectionResult(
                        characteristic_id="2",
                        balloon_number="2",
                        measured_value="2.02",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=5,
                        source_document=dim_file,
                        evidence=[ev(dim_file, 2, "balloon_2", "2 2.02 mm PASS")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=fair_file,
                document_type=DocumentType.FAIR,
                metadata={
                    "part_number": {"value": "BRKT-4421", "evidence": [ev(fair_file, 1, "part_number", "Part BRKT-4421")]},
                    "drawing_number": {"value": "DWG-4421", "evidence": [ev(fair_file, 1, "drawing_number", "Drawing DWG-4421")]},
                    "revision": {"value": "C", "evidence": [ev(fair_file, 1, "revision", "Rev C")]},
                    "customer_name": {"value": "Stellantis", "evidence": [ev(fair_file, 1, "customer_name", "Customer Stellantis")]},
                    "supplier_name": {"value": "Anatolia Precision", "evidence": [ev(fair_file, 1, "supplier_name", "Supplier Anatolia Precision")]},
                    "approval_status": {"value": "Open", "evidence": [ev(fair_file, 1, "approval_status", "Status Open")]},
                    "signatory": {"value": "Quality Engineer", "evidence": [ev(fair_file, 4, "signatory", "Signed by Quality Engineer")]},
                    "date": {"value": "2026-03-03", "evidence": [ev(fair_file, 1, "date", "Date 2026-03-03")]},
                },
                inspection_results=[
                    InspectionResult(
                        characteristic_id="1",
                        balloon_number="1",
                        measured_value="124.95",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=1,
                        source_document=fair_file,
                        evidence=[ev(fair_file, 2, "balloon_1", "1 124.95 mm Accept")],
                    ),
                    InspectionResult(
                        characteristic_id="2",
                        balloon_number="2",
                        measured_value="2.01",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=1,
                        source_document=fair_file,
                        evidence=[ev(fair_file, 2, "balloon_2", "2 2.01 mm Accept")],
                    ),
                ],
            ),
        ],
    )


def _ppap_ready_submission() -> SubmissionPackage:
    prefix = "CLP-9001"
    drawing_file = f"{prefix}_drawing_revA.pdf"
    psw_file = f"{prefix}_psw_revA.pdf"
    pfmea_file = f"{prefix}_pfmea_revA.xlsx"
    flow_file = f"{prefix}_process_flow_revA.pdf"
    control_file = f"{prefix}_control_plan_revA.xlsx"
    dim_file = f"{prefix}_dimensional_revA.xlsx"
    msa_file = f"{prefix}_msa_revA.xlsx"
    process_study_file = f"{prefix}_process_study_revA.xlsx"
    material_file = f"{prefix}_material_results_revA.pdf"

    return SubmissionPackage(
        submission_id="ppap-ready-001",
        submission_mode=SubmissionMode.PPAP,
        context=SubmissionContext(
            customer_oem="Bosch",
            requested_submission_mode=SubmissionMode.PPAP,
            ppap_level=3,
            part_number="CLP-9001",
            drawing_number="9001-D",
            revision="A",
            supplier_name="Eksen Metal",
            manufacturing_process="CNC Machining",
            material="Al 6061-T6",
        ),
        documents=[
            DocumentRecord(
                file_name=drawing_file,
                document_type=DocumentType.DESIGN_RECORD,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(drawing_file, 1, "part_number", "PART NO CLP-9001")]},
                    "drawing_number": {"value": "9001-D", "evidence": [ev(drawing_file, 1, "drawing_number", "DRAWING 9001-D")]},
                    "revision": {"value": "A", "evidence": [ev(drawing_file, 1, "revision", "REV A")]},
                    "material": {"value": "Al 6061-T6", "evidence": [ev(drawing_file, 1, "material", "MATERIAL AL 6061-T6")]},
                },
                drawing_characteristics=[
                    DrawingCharacteristic(
                        characteristic_id="5",
                        balloon_number="5",
                        description="Base width",
                        nominal="42.0",
                        tolerance="+/-0.10",
                        unit="mm",
                        source_document=drawing_file,
                        evidence=[ev(drawing_file, 2, "balloon_5", "5 WIDTH 42.0 +/-0.10")],
                    ),
                    DrawingCharacteristic(
                        characteristic_id="12",
                        balloon_number="12",
                        description="Bore diameter",
                        nominal="12.0",
                        tolerance="+/-0.03",
                        unit="mm",
                        characteristic_type=CharacteristicType.SPECIAL,
                        source_document=drawing_file,
                        evidence=[ev(drawing_file, 2, "balloon_12", "12 <SC> DIA 12.0 +/-0.03")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=psw_file,
                document_type=DocumentType.PSW,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(psw_file, 1, "part_number", "Part CLP-9001")]},
                    "drawing_number": {"value": "9001-D", "evidence": [ev(psw_file, 1, "drawing_number", "Drawing 9001-D")]},
                    "revision": {"value": "A", "evidence": [ev(psw_file, 1, "revision", "Rev A")]},
                    "customer_name": {"value": "Bosch", "evidence": [ev(psw_file, 1, "customer_name", "Customer Bosch")]},
                    "supplier_name": {"value": "Eksen Metal", "evidence": [ev(psw_file, 1, "supplier_name", "Supplier Eksen Metal")]},
                    "submission_reason": {"value": "Initial submission", "evidence": [ev(psw_file, 1, "submission_reason", "Initial submission")]},
                    "approval_status": {"value": "Submitted", "evidence": [ev(psw_file, 2, "approval_status", "Warrant Status Submitted")]},
                    "signatory": {"value": "Aylin Kara", "evidence": [ev(psw_file, 2, "signatory", "Signed Aylin Kara")]},
                    "date": {"value": "2026-03-04", "evidence": [ev(psw_file, 2, "date", "Date 2026-03-04")]},
                },
            ),
            DocumentRecord(
                file_name=pfmea_file,
                document_type=DocumentType.PFMEA,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(pfmea_file, 1, "part_number", "Part CLP-9001")]},
                    "revision": {"value": "A", "evidence": [ev(pfmea_file, 1, "revision", "Rev A")]},
                    "process_name": {"value": "CNC Machining", "evidence": [ev(pfmea_file, 1, "process_name", "Process CNC Machining")]},
                },
                pfmea_entries=[
                    PfmeaEntry(
                        step_id="10",
                        failure_mode="Incorrect stock removal",
                        severity_rating=6,
                        risk_priority=72,
                        evidence=[ev(pfmea_file, 2, "step_10", "Step 10 rough machining")],
                    ),
                    PfmeaEntry(
                        step_id="20",
                        failure_mode="Bore diameter out of tolerance",
                        severity_rating=8,
                        risk_priority=112,
                        special_characteristic_ids=["12"],
                        evidence=[ev(pfmea_file, 3, "step_20", "Step 20 finish bore characteristic 12")],
                    ),
                    PfmeaEntry(
                        step_id="30",
                        failure_mode="Final inspection miss due to record entry error",
                        severity_rating=5,
                        risk_priority=45,
                        evidence=[ev(pfmea_file, 4, "step_30", "Step 30 final inspection record entry")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=flow_file,
                document_type=DocumentType.PROCESS_FLOW,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(flow_file, 1, "part_number", "Part CLP-9001")]},
                    "revision": {"value": "A", "evidence": [ev(flow_file, 1, "revision", "Rev A")]},
                    "process_name": {"value": "CNC Machining", "evidence": [ev(flow_file, 1, "process_name", "Process CNC Machining")]},
                },
                process_flow_steps=[
                    ProcessFlowStep(step_id="10", step_name="Rough machining", sequence=10, evidence=[ev(flow_file, 2, "step_10", "10 Rough machining")]),
                    ProcessFlowStep(step_id="20", step_name="Finish bore", sequence=20, evidence=[ev(flow_file, 2, "step_20", "20 Finish bore")]),
                    ProcessFlowStep(step_id="30", step_name="Final inspection", sequence=30, evidence=[ev(flow_file, 2, "step_30", "30 Final inspection")]),
                ],
            ),
            DocumentRecord(
                file_name=control_file,
                document_type=DocumentType.CONTROL_PLAN,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(control_file, 1, "part_number", "Part CLP-9001")]},
                    "revision": {"value": "A", "evidence": [ev(control_file, 1, "revision", "Rev A")]},
                    "process_name": {"value": "CNC Machining", "evidence": [ev(control_file, 1, "process_name", "Process CNC Machining")]},
                },
                control_plan_entries=[
                    ControlPlanEntry(
                        step_id="10",
                        characteristic_ids=["5"],
                        control_method="First-off dimensional check",
                        reaction_plan="Stop machine, correct offset, re-verify",
                        sample_size=3,
                        evidence=[ev(control_file, 2, "step_10", "Step 10 characteristic 5")],
                    ),
                    ControlPlanEntry(
                        step_id="20",
                        characteristic_ids=["12"],
                        control_method="Bore gage with SPC",
                        reaction_plan="Contain lot, adjust tool wear offset, perform 100% sort until stability is restored",
                        sample_size=5,
                        evidence=[ev(control_file, 3, "step_20", "Step 20 special characteristic 12")],
                    ),
                    ControlPlanEntry(
                        step_id="30",
                        characteristic_ids=["5", "12"],
                        control_method="Final layout",
                        reaction_plan="Segregate and review",
                        sample_size=1,
                        evidence=[ev(control_file, 4, "step_30", "Step 30 final inspection")],
                    ),
                ],
                notes=["Reaction plan for non-special characteristic 5 is generic and could be more specific."],
            ),
            DocumentRecord(
                file_name=dim_file,
                document_type=DocumentType.DIMENSIONAL_RESULTS,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(dim_file, 1, "part_number", "Part CLP-9001")]},
                    "drawing_number": {"value": "9001-D", "evidence": [ev(dim_file, 1, "drawing_number", "Drawing 9001-D")]},
                    "revision": {"value": "A", "evidence": [ev(dim_file, 1, "revision", "Rev A")]},
                    "date": {"value": "2026-03-01", "evidence": [ev(dim_file, 1, "date", "Date 2026-03-01")]},
                },
                inspection_results=[
                    InspectionResult(
                        characteristic_id="5",
                        balloon_number="5",
                        measured_value="41.98",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=5,
                        source_document=dim_file,
                        evidence=[ev(dim_file, 2, "balloon_5", "5 41.98 mm PASS")],
                    ),
                    InspectionResult(
                        characteristic_id="12",
                        balloon_number="12",
                        measured_value="12.01",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=5,
                        source_document=dim_file,
                        evidence=[ev(dim_file, 2, "balloon_12", "12 12.01 mm PASS")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=msa_file,
                document_type=DocumentType.MSA,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(msa_file, 1, "part_number", "Part CLP-9001")]},
                    "revision": {"value": "A", "evidence": [ev(msa_file, 1, "revision", "Rev A")]},
                    "date": {"value": "2026-02-28", "evidence": [ev(msa_file, 1, "date", "Date 2026-02-28")]},
                },
                msa_studies=[
                    MsaStudy(
                        characteristic_id="12",
                        grr_percent=8.5,
                        ndc=7,
                        conclusion="Acceptable for production use",
                        evidence=[ev(msa_file, 2, "study_12", "GRR 8.5% NDC 7")],
                    )
                ],
            ),
            DocumentRecord(
                file_name=process_study_file,
                document_type=DocumentType.PROCESS_STUDY,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(process_study_file, 1, "part_number", "Part CLP-9001")]},
                    "revision": {"value": "A", "evidence": [ev(process_study_file, 1, "revision", "Rev A")]},
                    "date": {"value": "2026-03-01", "evidence": [ev(process_study_file, 1, "date", "Date 2026-03-01")]},
                },
                capability_studies=[
                    CapabilityStudy(
                        characteristic_id="12",
                        cpk=1.83,
                        ppk=1.62,
                        sample_size=125,
                        evidence=[ev(process_study_file, 2, "study_12", "Characteristic 12 Cpk 1.83 Ppk 1.62 n=125")],
                    )
                ],
            ),
            DocumentRecord(
                file_name=material_file,
                document_type=DocumentType.MATERIAL_RESULTS,
                classification_confidence=0.94,
                metadata={
                    "part_number": {"value": "CLP-9001", "evidence": [ev(material_file, 1, "part_number", "Part CLP-9001")]},
                    "revision": {"value": "A", "evidence": [ev(material_file, 1, "revision", "Rev A")]},
                    "date": {"value": "2026-02-27", "evidence": [ev(material_file, 1, "date", "Date 2026-02-27")]},
                    "material": {"value": "Al 6061-T6", "evidence": [ev(material_file, 1, "material", "Material Al 6061-T6")]},
                },
                certificates=[
                    CertificateRecord(
                        certificate_type="Mill Cert",
                        identifier="MC-6061-7781",
                        related_requirement="Al 6061-T6",
                        source_document=material_file,
                        evidence=[ev(material_file, 2, "certificate", "Cert MC-6061-7781")],
                    )
                ],
                notes=["Reaction plan wording for one non-critical feature is generic but does not break traceability."],
            ),
        ],
    )


def _conditional_fai_submission() -> SubmissionPackage:
    balloon_file = "AERO-118_ballooned_revD_scan.pdf"
    fair_file = "AERO-118_fair_revD_scan.xlsx"
    material_file = "AERO-118_material_cert_revD.pdf"

    return SubmissionPackage(
        submission_id="fai-conditional-001",
        submission_mode=SubmissionMode.FAI,
        context=SubmissionContext(
            customer_oem="Airbus",
            requested_submission_mode=SubmissionMode.FAI,
            part_number="AERO-118",
            drawing_number="AB-118",
            revision="D",
            supplier_name="Orbit Fabrication",
            manufacturing_process="Sheet metal forming",
            material="Ti-6Al-4V",
            industry_mode="aerospace",
        ),
        documents=[
            DocumentRecord(
                file_name=balloon_file,
                document_type=DocumentType.BALLOONED_DRAWING,
                classification_confidence=0.68,
                metadata={
                    "part_number": {
                        "value": "AERO-118",
                        "status": ExtractionStatus.INFERRED_LOW_CONFIDENCE,
                        "confidence": 0.61,
                        "evidence": [ev(balloon_file, 1, "part_number", "AER0-118", 0.61)],
                    },
                    "drawing_number": {
                        "value": "AB-118",
                        "evidence": [ev(balloon_file, 1, "drawing_number", "AB-118")],
                    },
                    "revision": {
                        "value": "D",
                        "evidence": [ev(balloon_file, 1, "revision", "REV D")],
                    },
                },
                drawing_characteristics=[
                    DrawingCharacteristic(
                        characteristic_id="101",
                        balloon_number="101",
                        description="Edge distance",
                        nominal="16.0",
                        tolerance="+/-0.10",
                        unit="mm",
                        source_document=balloon_file,
                        evidence=[ev(balloon_file, 2, "balloon_101", "101")],
                    ),
                    DrawingCharacteristic(
                        characteristic_id="102",
                        balloon_number="102",
                        description="Hole diameter",
                        nominal="6.35",
                        tolerance="+0.05/-0.00",
                        unit="mm",
                        characteristic_type=CharacteristicType.SPECIAL,
                        source_document=balloon_file,
                        evidence=[ev(balloon_file, 2, "balloon_102", "102")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=fair_file,
                document_type=DocumentType.FAIR,
                metadata={
                    "part_number": {"value": "AERO-118", "evidence": [ev(fair_file, 1, "part_number", "Part AERO-118")]},
                    "drawing_number": {"value": "AB-118", "evidence": [ev(fair_file, 1, "drawing_number", "Drawing AB-118")]},
                    "revision": {"value": "D", "evidence": [ev(fair_file, 1, "revision", "Rev D")]},
                    "customer_name": {"value": "Airbus", "evidence": [ev(fair_file, 1, "customer_name", "Customer Airbus")]},
                    "supplier_name": {"value": "Orbit Fabrication", "evidence": [ev(fair_file, 1, "supplier_name", "Supplier Orbit Fabrication")]},
                    "approval_status": {
                        "value": "Under Review",
                        "evidence": [ev(fair_file, 1, "approval_status", "Status Under Review")],
                    },
                    "signatory": {
                        "value": "M. Yildiz",
                        "evidence": [ev(fair_file, 4, "signatory", "Signed M. Yildiz")],
                    },
                    "date": {"value": "2026-03-05", "evidence": [ev(fair_file, 1, "date", "Date 2026-03-05")]},
                },
                inspection_results=[
                    InspectionResult(
                        characteristic_id="101",
                        balloon_number="101",
                        measured_value="16.02",
                        unit="mm",
                        result=MeasurementStatus.PASS,
                        sample_size=1,
                        source_document=fair_file,
                        evidence=[ev(fair_file, 2, "balloon_101", "101 16.02 mm")],
                    ),
                    InspectionResult(
                        characteristic_id="102",
                        balloon_number="102",
                        measured_value="6.34",
                        unit=None,
                        result=MeasurementStatus.PASS,
                        sample_size=1,
                        source_document=fair_file,
                        evidence=[ev(fair_file, 2, "balloon_102", "102 6.34")],
                    ),
                ],
            ),
            DocumentRecord(
                file_name=material_file,
                document_type=DocumentType.MATERIAL_CERTIFICATE,
                metadata={
                    "material": {"value": "Ti-6Al-4V", "evidence": [ev(material_file, 1, "material", "Material Ti-6Al-4V")]},
                    "date": {"value": "2026-03-01", "evidence": [ev(material_file, 1, "date", "Date 2026-03-01")]},
                },
                certificates=[
                    CertificateRecord(
                        certificate_type="Material Certification",
                        identifier="CERT-TI-4427",
                        related_requirement="Ti-6Al-4V",
                        source_document=material_file,
                        evidence=[ev(material_file, 2, "certificate", "CERT-TI-4427")],
                    )
                ],
            ),
        ],
    )
