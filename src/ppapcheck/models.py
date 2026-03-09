from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubmissionMode(StrEnum):
    PPAP = "PPAP"
    FAI = "FAI"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


class Decision(StrEnum):
    PASS = "PASS"
    PASS_WITH_OBSERVATIONS = "PASS_WITH_OBSERVATIONS"
    CONDITIONAL = "CONDITIONAL"
    FAIL = "FAIL"
    BLOCK_SUBMISSION = "BLOCK_SUBMISSION"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Severity(StrEnum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    OBSERVATION = "Observation"


class PresenceStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    OPTIONAL = "optional"
    UNCLEAR = "unclear"


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"


class ExtractionStatus(StrEnum):
    VERIFIED = "verified"
    NOT_FOUND = "not found"
    NOT_LEGIBLE = "not legible"
    INCONSISTENT = "inconsistent"
    INFERRED_LOW_CONFIDENCE = "inferred with low confidence"
    REQUIRES_MANUAL_REVIEW = "requires manual review"


class MeasurementStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"


class CharacteristicType(StrEnum):
    STANDARD = "standard"
    SPECIAL = "special"
    CRITICAL = "critical"


class DocumentType(StrEnum):
    PSW = "PSW"
    DESIGN_RECORD = "DESIGN_RECORD"
    ENGINEERING_CHANGE = "ENGINEERING_CHANGE"
    CUSTOMER_ENGINEERING_APPROVAL = "CUSTOMER_ENGINEERING_APPROVAL"
    DFMEA = "DFMEA"
    PFMEA = "PFMEA"
    PROCESS_FLOW = "PROCESS_FLOW"
    CONTROL_PLAN = "CONTROL_PLAN"
    MSA = "MSA"
    DIMENSIONAL_RESULTS = "DIMENSIONAL_RESULTS"
    MATERIAL_RESULTS = "MATERIAL_RESULTS"
    PERFORMANCE_RESULTS = "PERFORMANCE_RESULTS"
    PROCESS_STUDY = "PROCESS_STUDY"
    QUALIFIED_LAB = "QUALIFIED_LAB"
    AAR = "AAR"
    SAMPLE_PART = "SAMPLE_PART"
    MASTER_SAMPLE = "MASTER_SAMPLE"
    CHECKING_AIDS = "CHECKING_AIDS"
    CUSTOMER_REQUIREMENTS = "CUSTOMER_REQUIREMENTS"
    PACKAGING_LABELING = "PACKAGING_LABELING"
    OEM_SPECIFIC = "OEM_SPECIFIC"
    BALLOONED_DRAWING = "BALLOONED_DRAWING"
    FAIR = "FAIR"
    MATERIAL_CERTIFICATE = "MATERIAL_CERTIFICATE"
    SPECIAL_PROCESS_CERTIFICATE = "SPECIAL_PROCESS_CERTIFICATE"
    MEASUREMENT_TRACEABILITY = "MEASUREMENT_TRACEABILITY"
    NONCONFORMANCE_RECORD = "NONCONFORMANCE_RECORD"
    SIGN_OFF_RECORD = "SIGN_OFF_RECORD"
    UNKNOWN = "UNKNOWN"


DOCUMENT_LABELS: dict[DocumentType, str] = {
    DocumentType.PSW: "Part Submission Warrant (PSW)",
    DocumentType.DESIGN_RECORD: "Design Record / Drawing",
    DocumentType.ENGINEERING_CHANGE: "Engineering Change Document",
    DocumentType.CUSTOMER_ENGINEERING_APPROVAL: "Customer Engineering Approval",
    DocumentType.DFMEA: "DFMEA",
    DocumentType.PFMEA: "PFMEA",
    DocumentType.PROCESS_FLOW: "Process Flow Diagram",
    DocumentType.CONTROL_PLAN: "Control Plan",
    DocumentType.MSA: "MSA Study",
    DocumentType.DIMENSIONAL_RESULTS: "Dimensional Results",
    DocumentType.MATERIAL_RESULTS: "Material Test Results",
    DocumentType.PERFORMANCE_RESULTS: "Performance Test Results",
    DocumentType.PROCESS_STUDY: "Initial Process Study",
    DocumentType.QUALIFIED_LAB: "Qualified Laboratory Documentation",
    DocumentType.AAR: "Appearance Approval Report",
    DocumentType.SAMPLE_PART: "Sample Production Parts",
    DocumentType.MASTER_SAMPLE: "Master Sample",
    DocumentType.CHECKING_AIDS: "Checking Aids",
    DocumentType.CUSTOMER_REQUIREMENTS: "Customer-Specific Requirements",
    DocumentType.PACKAGING_LABELING: "Packaging / Labeling Requirements",
    DocumentType.OEM_SPECIFIC: "OEM-Specific Evidence",
    DocumentType.BALLOONED_DRAWING: "Ballooned Drawing",
    DocumentType.FAIR: "First Article Inspection Report (FAIR)",
    DocumentType.MATERIAL_CERTIFICATE: "Material Certification",
    DocumentType.SPECIAL_PROCESS_CERTIFICATE: "Special Process Certification",
    DocumentType.MEASUREMENT_TRACEABILITY: "Measurement Traceability Evidence",
    DocumentType.NONCONFORMANCE_RECORD: "Nonconformance Record",
    DocumentType.SIGN_OFF_RECORD: "Sign-Off Record",
    DocumentType.UNKNOWN: "Unknown Document Type",
}

DOCUMENT_TYPE_ALIASES: dict[str, DocumentType] = {
    "psw": DocumentType.PSW,
    "part submission warrant": DocumentType.PSW,
    "design record": DocumentType.DESIGN_RECORD,
    "drawing": DocumentType.DESIGN_RECORD,
    "engineering change": DocumentType.ENGINEERING_CHANGE,
    "customer engineering approval": DocumentType.CUSTOMER_ENGINEERING_APPROVAL,
    "dfmea": DocumentType.DFMEA,
    "pfmea": DocumentType.PFMEA,
    "process flow": DocumentType.PROCESS_FLOW,
    "control plan": DocumentType.CONTROL_PLAN,
    "msa": DocumentType.MSA,
    "dimensional": DocumentType.DIMENSIONAL_RESULTS,
    "material results": DocumentType.MATERIAL_RESULTS,
    "performance results": DocumentType.PERFORMANCE_RESULTS,
    "process study": DocumentType.PROCESS_STUDY,
    "lab": DocumentType.QUALIFIED_LAB,
    "aar": DocumentType.AAR,
    "customer requirements": DocumentType.CUSTOMER_REQUIREMENTS,
    "packaging": DocumentType.PACKAGING_LABELING,
    "ballooned drawing": DocumentType.BALLOONED_DRAWING,
    "fair": DocumentType.FAIR,
    "first article": DocumentType.FAIR,
    "material certificate": DocumentType.MATERIAL_CERTIFICATE,
    "special process certificate": DocumentType.SPECIAL_PROCESS_CERTIFICATE,
    "measurement traceability": DocumentType.MEASUREMENT_TRACEABILITY,
    "nonconformance": DocumentType.NONCONFORMANCE_RECORD,
    "sign off": DocumentType.SIGN_OFF_RECORD,
}


def canonical_metadata_key(value: str) -> str:
    key = value.strip().replace("-", "_").replace(" ", "_")
    key = key.replace("/", "_").replace("__", "_")
    return key.lower()


def display_document_type(document_type: DocumentType) -> str:
    return DOCUMENT_LABELS[document_type]


def parse_document_type(value: Any) -> DocumentType:
    if isinstance(value, DocumentType):
        return value
    if value is None:
        return DocumentType.UNKNOWN
    text = str(value).strip()
    if not text:
        return DocumentType.UNKNOWN
    normalized = text.upper()
    if normalized in DocumentType.__members__:
        return DocumentType[normalized]
    alias = DOCUMENT_TYPE_ALIASES.get(text.strip().lower())
    return alias or DocumentType.UNKNOWN


class EvidenceRef(BaseModel):
    file_name: str
    page_number: int | None = None
    section_name: str | None = None
    field_name: str | None = None
    snippet: str | None = None
    confidence: float = 1.0

    def summary(self) -> str:
        parts = [self.file_name]
        if self.page_number is not None:
            parts.append(f"p.{self.page_number}")
        if self.section_name:
            parts.append(self.section_name)
        if self.field_name:
            parts.append(self.field_name)
        return " | ".join(parts)


class ExtractedValue(BaseModel):
    value: Any | None = None
    status: ExtractionStatus = ExtractionStatus.VERIFIED
    confidence: float = 1.0
    evidence: list[EvidenceRef] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, value: Any) -> ExtractionStatus:
        if isinstance(value, ExtractionStatus):
            return value
        if value is None:
            return ExtractionStatus.NOT_FOUND
        text = str(value).strip().lower()
        for item in ExtractionStatus:
            if item.value == text:
                return item
        if text in {"missing", "not_found"}:
            return ExtractionStatus.NOT_FOUND
        if text in {"low_confidence", "low confidence"}:
            return ExtractionStatus.INFERRED_LOW_CONFIDENCE
        if text in {"manual_review", "manual review"}:
            return ExtractionStatus.REQUIRES_MANUAL_REVIEW
        return ExtractionStatus.VERIFIED

    @property
    def is_present(self) -> bool:
        if self.status in {ExtractionStatus.NOT_FOUND, ExtractionStatus.NOT_LEGIBLE}:
            return False
        if self.value is None:
            return False
        if isinstance(self.value, str) and not self.value.strip():
            return False
        return True

    @property
    def text(self) -> str:
        if self.value is None:
            return ""
        if isinstance(self.value, bool):
            return "Yes" if self.value else "No"
        if isinstance(self.value, (list, dict)):
            return json.dumps(self.value, ensure_ascii=True)
        return str(self.value)


class DrawingCharacteristic(BaseModel):
    characteristic_id: str
    balloon_number: str | None = None
    description: str
    nominal: str | None = None
    tolerance: str | None = None
    unit: str | None = None
    characteristic_type: CharacteristicType = CharacteristicType.STANDARD
    source_document: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class InspectionResult(BaseModel):
    characteristic_id: str | None = None
    balloon_number: str | None = None
    measured_value: str | None = None
    unit: str | None = None
    result: MeasurementStatus = MeasurementStatus.UNCLEAR
    sample_size: int | None = None
    source_document: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ProcessFlowStep(BaseModel):
    step_id: str
    step_name: str
    sequence: int
    evidence: list[EvidenceRef] = Field(default_factory=list)


class PfmeaEntry(BaseModel):
    step_id: str
    failure_mode: str
    effect: str | None = None
    cause: str | None = None
    current_control: str | None = None
    severity_rating: int | None = None
    risk_priority: int | None = None
    special_characteristic_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ControlPlanEntry(BaseModel):
    step_id: str
    characteristic_ids: list[str] = Field(default_factory=list)
    control_method: str | None = None
    reaction_plan: str | None = None
    sample_size: int | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class CapabilityStudy(BaseModel):
    characteristic_id: str
    cpk: float | None = None
    ppk: float | None = None
    sample_size: int | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class MsaStudy(BaseModel):
    characteristic_id: str | None = None
    grr_percent: float | None = None
    ndc: int | None = None
    conclusion: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class CertificateRecord(BaseModel):
    certificate_type: str
    identifier: str | None = None
    related_requirement: str | None = None
    source_document: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class DocumentRecord(BaseModel):
    document_id: str | None = None
    file_name: str
    document_type: DocumentType = DocumentType.UNKNOWN
    classification_confidence: float = 1.0
    metadata: dict[str, ExtractedValue] = Field(default_factory=dict)
    drawing_characteristics: list[DrawingCharacteristic] = Field(default_factory=list)
    inspection_results: list[InspectionResult] = Field(default_factory=list)
    process_flow_steps: list[ProcessFlowStep] = Field(default_factory=list)
    pfmea_entries: list[PfmeaEntry] = Field(default_factory=list)
    control_plan_entries: list[ControlPlanEntry] = Field(default_factory=list)
    capability_studies: list[CapabilityStudy] = Field(default_factory=list)
    msa_studies: list[MsaStudy] = Field(default_factory=list)
    certificates: list[CertificateRecord] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("document_type", mode="before")
    @classmethod
    def coerce_document_type(cls, value: Any) -> DocumentType:
        return parse_document_type(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = canonical_metadata_key(key)
            if isinstance(item, ExtractedValue):
                normalized[normalized_key] = item
                continue
            if isinstance(item, dict) and any(
                field in item for field in ("value", "status", "confidence", "evidence")
            ):
                normalized[normalized_key] = item
                continue
            if item is None or (isinstance(item, str) and not item.strip()):
                normalized[normalized_key] = {
                    "value": None,
                    "status": ExtractionStatus.NOT_FOUND,
                    "confidence": 0.0,
                }
            else:
                normalized[normalized_key] = {
                    "value": item,
                    "status": ExtractionStatus.VERIFIED,
                    "confidence": 0.95,
                }
        return normalized

    @property
    def document_label(self) -> str:
        return display_document_type(self.document_type)

    def get_field(self, key: str) -> ExtractedValue:
        return self.metadata.get(canonical_metadata_key(key), ExtractedValue(status=ExtractionStatus.NOT_FOUND, confidence=0.0))

    def get_text(self, key: str) -> str:
        return self.get_field(key).text


class SubmissionContext(BaseModel):
    customer_oem: str | None = None
    requested_submission_mode: SubmissionMode = SubmissionMode.UNKNOWN
    ppap_level: int | None = None
    part_number: str | None = None
    drawing_number: str | None = None
    revision: str | None = None
    supplier_name: str | None = None
    manufacturing_process: str | None = None
    commodity: str | None = None
    material: str | None = None
    special_processes: list[str] = Field(default_factory=list)
    customer_specific_rules: list[str] = Field(default_factory=list)
    industry_mode: str = "automotive"


class SubmissionPackage(BaseModel):
    submission_id: str
    submission_mode: SubmissionMode = SubmissionMode.UNKNOWN
    context: SubmissionContext = Field(default_factory=SubmissionContext)
    documents: list[DocumentRecord] = Field(default_factory=list)


class RequirementStatus(BaseModel):
    document_type: DocumentType
    document_label: str
    status: PresenceStatus
    rationale: str
    requirement_source: str
    severity_if_missing: Severity | None = None
    blocking_if_missing: bool = False
    present_files: list[str] = Field(default_factory=list)


class DocumentInventoryItem(BaseModel):
    file_name: str
    document_type: DocumentType
    document_label: str
    classification_confidence: float
    key_metadata: dict[str, str] = Field(default_factory=dict)
    structured_counts: dict[str, int] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)


class MetadataMasterRecord(BaseModel):
    part_number: str = ""
    drawing_number: str = ""
    revision: str = ""
    customer: str = ""
    supplier: str = ""
    process: str = ""
    material: str = ""


class MeasurementSummary(BaseModel):
    total_characteristics: int = 0
    total_results: int = 0
    passed_results: int = 0
    failed_results: int = 0
    unclear_results: int = 0
    numeric_results: int = 0
    attribute_results: int = 0
    source_documents: list[str] = Field(default_factory=list)


class CheckResult(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity | None = None
    description: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = 1.0
    suggested_action: str | None = None


class ValidationFinding(BaseModel):
    finding_id: str
    category: str
    severity: Severity
    title: str
    description: str
    blocking: bool = False
    evidence: list[EvidenceRef] = Field(default_factory=list)
    related_documents: list[DocumentType] = Field(default_factory=list)
    related_characteristics: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    suggested_action: str | None = None


class AuditLogEntry(BaseModel):
    stage: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    submission_mode: SubmissionMode
    overall_decision: Decision
    overall_score: int
    confidence: ConfidenceLevel
    document_inventory: list[DocumentInventoryItem]
    required_documents: list[RequirementStatus]
    missing_documents: list[str]
    metadata_master_record: MetadataMasterRecord
    measurement_summary: MeasurementSummary = Field(default_factory=MeasurementSummary)
    cross_document_conflicts: list[ValidationFinding]
    ppap_checks: list[CheckResult]
    fai_checks: list[CheckResult]
    traceability_checks: list[CheckResult]
    technical_findings: list[ValidationFinding]
    nonconformities: list[ValidationFinding]
    manual_review_flags: list[ValidationFinding]
    recommended_actions: list[str]
    expert_report: str
