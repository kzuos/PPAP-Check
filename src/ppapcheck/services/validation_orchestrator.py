from __future__ import annotations

from ppapcheck.models import Severity, SubmissionPackage, ValidationReport
from ppapcheck.services.audit_log_service import AuditLogService
from ppapcheck.services.cross_document_validator import CrossDocumentValidator
from ppapcheck.services.document_classifier import DocumentClassifier
from ppapcheck.services.document_ingestion_service import DocumentIngestionService
from ppapcheck.services.extraction_service import ExtractionService
from ppapcheck.services.report_generator import ReportGenerator
from ppapcheck.services.requirement_catalog import RequirementCatalog
from ppapcheck.services.scoring_engine import ScoringEngine
from ppapcheck.services.standards_rule_engine import StandardsRuleEngine
from ppapcheck.services.technical_quality_validator import TechnicalQualityValidator
from ppapcheck.services.traceability_engine import TraceabilityEngine


class ValidationOrchestrator:
    def __init__(self) -> None:
        self.audit_log = AuditLogService()
        self.requirement_catalog = RequirementCatalog()
        self.ingestion_service = DocumentIngestionService()
        self.classifier = DocumentClassifier()
        self.extraction_service = ExtractionService()
        self.standards_rule_engine = StandardsRuleEngine(self.requirement_catalog)
        self.cross_document_validator = CrossDocumentValidator()
        self.traceability_engine = TraceabilityEngine()
        self.technical_quality_validator = TechnicalQualityValidator()
        self.scoring_engine = ScoringEngine()
        self.report_generator = ReportGenerator()

    def validate(self, package: SubmissionPackage) -> ValidationReport:
        self.audit_log.record(package.submission_id, "ingestion", "Starting submission ingestion", document_count=len(package.documents))
        package = self.ingestion_service.ingest(package)
        package = package.model_copy(update={"documents": self.classifier.classify_all(package.documents)})
        package = self.extraction_service.normalize(package)

        mode = self.requirement_catalog.resolve_submission_mode(package)
        self.audit_log.record(package.submission_id, "classification", "Resolved submission mode", mode=mode)

        standards = self.standards_rule_engine.evaluate(package, mode)
        self.audit_log.record(
            package.submission_id,
            "standards_rule_engine",
            "Evaluated document presence and field completeness",
            required_documents=len(standards.required_documents),
            findings=len(standards.nonconformities),
        )

        metadata_master_record, conflicts = self.cross_document_validator.evaluate(package)
        self.audit_log.record(
            package.submission_id,
            "cross_document_validator",
            "Evaluated cross-document consistency",
            conflicts=len(conflicts),
        )

        traceability_checks, traceability_findings = self.traceability_engine.evaluate(package, mode)
        self.audit_log.record(
            package.submission_id,
            "traceability_engine",
            "Evaluated traceability links",
            checks=len(traceability_checks),
            findings=len(traceability_findings),
        )

        technical_findings = self.technical_quality_validator.evaluate(package, mode)
        measurement_summary = self.technical_quality_validator.summarize_measurements(package)
        self.audit_log.record(
            package.submission_id,
            "technical_quality",
            "Evaluated technical quality",
            findings=len(technical_findings),
        )

        nonconformities = standards.nonconformities + conflicts + traceability_findings + technical_findings
        recommended_actions = self.report_generator.collect_recommended_actions(
            nonconformities, standards.manual_review_flags
        )
        score, decision, confidence = self.scoring_engine.score(
            nonconformities, standards.manual_review_flags
        )

        report = ValidationReport(
            submission_mode=mode,
            overall_decision=decision,
            overall_score=score,
            confidence=confidence,
            document_inventory=standards.document_inventory,
            required_documents=standards.required_documents,
            missing_documents=[
                requirement.document_label
                for requirement in standards.required_documents
                if requirement.status.value == "missing"
            ],
            metadata_master_record=metadata_master_record,
            measurement_summary=measurement_summary,
            cross_document_conflicts=conflicts,
            ppap_checks=standards.ppap_checks,
            fai_checks=standards.fai_checks,
            traceability_checks=traceability_checks,
            technical_findings=technical_findings,
            nonconformities=sorted(
                nonconformities,
                key=lambda finding: (
                    finding.blocking is False,
                    {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2, Severity.OBSERVATION: 3}[finding.severity],
                    finding.title,
                ),
            ),
            manual_review_flags=standards.manual_review_flags,
            recommended_actions=recommended_actions,
            expert_report="",
        )
        expert_report = self.report_generator.generate_expert_report(report)
        final_report = report.model_copy(update={"expert_report": expert_report})
        self.audit_log.record(
            package.submission_id,
            "report_generation",
            "Generated validation report",
            decision=decision,
            score=score,
        )
        return final_report
