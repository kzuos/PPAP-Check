from __future__ import annotations

from dataclasses import dataclass

from ppapcheck.models import (
    DocumentType,
    PresenceStatus,
    RequirementStatus,
    Severity,
    SubmissionMode,
    SubmissionPackage,
    display_document_type,
)


@dataclass(frozen=True)
class RequirementDescriptor:
    document_type: DocumentType
    rationale: str
    requirement_source: str
    required: bool = True
    severity_if_missing: Severity | None = None
    blocking_if_missing: bool = False


PPAP_KEY_TYPES = {
    DocumentType.PSW,
    DocumentType.DESIGN_RECORD,
    DocumentType.PFMEA,
    DocumentType.PROCESS_FLOW,
    DocumentType.CONTROL_PLAN,
    DocumentType.MSA,
    DocumentType.DIMENSIONAL_RESULTS,
    DocumentType.MATERIAL_RESULTS,
    DocumentType.PROCESS_STUDY,
}

FAI_KEY_TYPES = {
    DocumentType.BALLOONED_DRAWING,
    DocumentType.FAIR,
    DocumentType.MATERIAL_CERTIFICATE,
}

PPAP_LEVEL_BASELINES: dict[int, list[RequirementDescriptor]] = {
    1: [
        RequirementDescriptor(
            document_type=DocumentType.PSW,
            rationale="PPAP Level 1 requires submission identity and warrant evidence.",
            requirement_source="Baseline PPAP level 1 rule",
            severity_if_missing=Severity.CRITICAL,
            blocking_if_missing=True,
        ),
        RequirementDescriptor(
            document_type=DocumentType.DESIGN_RECORD,
            rationale="The design record establishes part identity, drawing number, and revision.",
            requirement_source="Baseline PPAP level 1 rule",
            severity_if_missing=Severity.CRITICAL,
            blocking_if_missing=True,
        ),
    ],
    2: [
        RequirementDescriptor(
            document_type=DocumentType.PSW,
            rationale="PPAP Level 2 requires submission identity and warrant evidence.",
            requirement_source="Baseline PPAP level 2 rule",
            severity_if_missing=Severity.CRITICAL,
            blocking_if_missing=True,
        ),
        RequirementDescriptor(
            document_type=DocumentType.DESIGN_RECORD,
            rationale="The design record establishes part identity, drawing number, and revision.",
            requirement_source="Baseline PPAP level 2 rule",
            severity_if_missing=Severity.CRITICAL,
            blocking_if_missing=True,
        ),
        RequirementDescriptor(
            document_type=DocumentType.DIMENSIONAL_RESULTS,
            rationale="Dimensional verification is required to show the part matches the released drawing.",
            requirement_source="Baseline PPAP level 2 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.MATERIAL_RESULTS,
            rationale="Material evidence is required when design material is specified.",
            requirement_source="Baseline PPAP level 2 rule",
            severity_if_missing=Severity.MAJOR,
        ),
    ],
    3: [
        RequirementDescriptor(
            document_type=DocumentType.PSW,
            rationale="PSW is the formal PPAP submission record.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.CRITICAL,
            blocking_if_missing=True,
        ),
        RequirementDescriptor(
            document_type=DocumentType.DESIGN_RECORD,
            rationale="Released design records are required to verify configuration and accountability.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.CRITICAL,
            blocking_if_missing=True,
        ),
        RequirementDescriptor(
            document_type=DocumentType.PFMEA,
            rationale="PFMEA is required to show process risk analysis and controls.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.PROCESS_FLOW,
            rationale="Process flow is required to establish the manufacturing sequence used by PFMEA and the control plan.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.CONTROL_PLAN,
            rationale="Control plan is required to show how process and product characteristics are controlled.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.MSA,
            rationale="MSA evidence is required to support measurement credibility.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.DIMENSIONAL_RESULTS,
            rationale="Dimensional results are required to verify drawing characteristics.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.MATERIAL_RESULTS,
            rationale="Material test evidence is required when material is specified.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
        RequirementDescriptor(
            document_type=DocumentType.PROCESS_STUDY,
            rationale="Initial process study evidence is required for production readiness.",
            requirement_source="Baseline PPAP level 3 rule",
            severity_if_missing=Severity.MAJOR,
        ),
    ],
}

PPAP_OPTIONAL_DESCRIPTORS = [
    RequirementDescriptor(
        document_type=DocumentType.DFMEA,
        rationale="DFMEA is required only when the supplier has design responsibility.",
        requirement_source="Conditional PPAP rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.ENGINEERING_CHANGE,
        rationale="Engineering change evidence is required only when the submission is driven by a change.",
        requirement_source="Conditional PPAP rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.CUSTOMER_ENGINEERING_APPROVAL,
        rationale="Customer engineering approval is required only when requested by the customer.",
        requirement_source="Conditional PPAP rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.AAR,
        rationale="Appearance approval is required only for appearance items.",
        requirement_source="Conditional PPAP rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.CHECKING_AIDS,
        rationale="Checking aid evidence is required only when dedicated aids are used.",
        requirement_source="Conditional PPAP rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.PACKAGING_LABELING,
        rationale="Packaging and labeling evidence is required when the customer defines packaging controls.",
        requirement_source="Conditional PPAP rule",
        required=False,
    ),
]

FAI_REQUIRED_DESCRIPTORS = [
    RequirementDescriptor(
        document_type=DocumentType.BALLOONED_DRAWING,
        rationale="A ballooned drawing is required to establish full characteristic accountability.",
        requirement_source="Baseline FAI rule",
        severity_if_missing=Severity.CRITICAL,
        blocking_if_missing=True,
    ),
    RequirementDescriptor(
        document_type=DocumentType.FAIR,
        rationale="A FAIR is required to record first article accountability and sign-off.",
        requirement_source="Baseline FAI rule",
        severity_if_missing=Severity.CRITICAL,
        blocking_if_missing=True,
    ),
    RequirementDescriptor(
        document_type=DocumentType.MATERIAL_CERTIFICATE,
        rationale="Material certification is required when the part drawing defines material requirements.",
        requirement_source="Baseline FAI rule",
        severity_if_missing=Severity.MAJOR,
    ),
]

FAI_OPTIONAL_DESCRIPTORS = [
    RequirementDescriptor(
        document_type=DocumentType.SPECIAL_PROCESS_CERTIFICATE,
        rationale="Special process certification is required only when special processes apply.",
        requirement_source="Conditional FAI rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.MEASUREMENT_TRACEABILITY,
        rationale="Separate traceability evidence is required only when traceability is not embedded in the FAIR or gage records.",
        requirement_source="Conditional FAI rule",
        required=False,
    ),
    RequirementDescriptor(
        document_type=DocumentType.NONCONFORMANCE_RECORD,
        rationale="Disposition evidence is required only when nonconformances occurred during the first article.",
        requirement_source="Conditional FAI rule",
        required=False,
    ),
]


class RequirementCatalog:
    def resolve_submission_mode(self, package: SubmissionPackage) -> SubmissionMode:
        if package.submission_mode != SubmissionMode.UNKNOWN:
            return package.submission_mode
        if package.context.requested_submission_mode != SubmissionMode.UNKNOWN:
            return package.context.requested_submission_mode

        document_types = {document.document_type for document in package.documents}
        has_ppap = bool(document_types & PPAP_KEY_TYPES)
        has_fai = bool(document_types & FAI_KEY_TYPES)
        if has_ppap and has_fai:
            return SubmissionMode.HYBRID
        if has_ppap:
            return SubmissionMode.PPAP
        if has_fai:
            return SubmissionMode.FAI
        return SubmissionMode.UNKNOWN

    def applicable_requirements(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> list[RequirementDescriptor]:
        descriptors: list[RequirementDescriptor] = []
        if mode in {SubmissionMode.PPAP, SubmissionMode.HYBRID}:
            level = package.context.ppap_level or 3
            descriptors.extend(PPAP_LEVEL_BASELINES[min(max(level, 1), 3)])
            descriptors.extend(PPAP_OPTIONAL_DESCRIPTORS)
            if package.context.customer_specific_rules:
                descriptors.append(
                    RequirementDescriptor(
                        document_type=DocumentType.CUSTOMER_REQUIREMENTS,
                        rationale="Customer-specific requirements were provided in the submission context.",
                        requirement_source="Submission context",
                        severity_if_missing=Severity.MAJOR,
                    )
                )
            else:
                descriptors.append(
                    RequirementDescriptor(
                        document_type=DocumentType.CUSTOMER_REQUIREMENTS,
                        rationale="No customer-specific requirement set was supplied, so separate evidence is optional in this baseline review.",
                        requirement_source="Submission context",
                        required=False,
                    )
                )

        if mode in {SubmissionMode.FAI, SubmissionMode.HYBRID}:
            descriptors.extend(FAI_REQUIRED_DESCRIPTORS)
            descriptors.extend(FAI_OPTIONAL_DESCRIPTORS)
            if package.context.special_processes:
                descriptors.append(
                    RequirementDescriptor(
                        document_type=DocumentType.SPECIAL_PROCESS_CERTIFICATE,
                        rationale="Special processes were declared in the submission context.",
                        requirement_source="Submission context",
                        severity_if_missing=Severity.MAJOR,
                    )
                )

        unique: dict[DocumentType, RequirementDescriptor] = {}
        for descriptor in descriptors:
            current = unique.get(descriptor.document_type)
            if current is None or (descriptor.required and not current.required):
                unique[descriptor.document_type] = descriptor
        return list(unique.values())

    def build_requirement_statuses(
        self, package: SubmissionPackage, mode: SubmissionMode
    ) -> list[RequirementStatus]:
        requirements = self.applicable_requirements(package, mode)
        present_by_type: dict[DocumentType, list[str]] = {}
        for document in package.documents:
            present_by_type.setdefault(document.document_type, []).append(document.file_name)

        statuses: list[RequirementStatus] = []
        for requirement in requirements:
            files = present_by_type.get(requirement.document_type, [])
            if files:
                status = PresenceStatus.PRESENT
            elif requirement.required:
                status = PresenceStatus.MISSING
            else:
                status = PresenceStatus.OPTIONAL
            statuses.append(
                RequirementStatus(
                    document_type=requirement.document_type,
                    document_label=display_document_type(requirement.document_type),
                    status=status,
                    rationale=requirement.rationale,
                    requirement_source=requirement.requirement_source,
                    severity_if_missing=requirement.severity_if_missing,
                    blocking_if_missing=requirement.blocking_if_missing,
                    present_files=files,
                )
            )
        return statuses

