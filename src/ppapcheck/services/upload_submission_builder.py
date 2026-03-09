from __future__ import annotations

import csv
import io
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from pypdf import PdfReader

from ppapcheck.models import (
    CertificateRecord,
    CharacteristicType,
    ControlPlanEntry,
    DocumentRecord,
    DocumentType,
    DrawingCharacteristic,
    EvidenceRef,
    ExtractedValue,
    ExtractionStatus,
    InspectionResult,
    MeasurementStatus,
    PfmeaEntry,
    ProcessFlowStep,
    SubmissionContext,
    SubmissionMode,
    SubmissionPackage,
)


@dataclass
class TextFragment:
    text: str
    page_number: int | None = None
    section_name: str | None = None


@dataclass
class TableSection:
    section_name: str
    rows: list[list[str]]


@dataclass
class ParsedUploadDocument:
    document: DocumentRecord
    warnings: list[str]


@dataclass
class UploadBuildResult:
    package: SubmissionPackage
    warnings: list[str]


FIELD_PATTERNS: dict[str, list[tuple[re.Pattern[str], float]]] = {
    "part_number": [
        (re.compile(r"(?:part(?:\s+number|\s+no\.?|#)?|p/?n)\s*[:#-]\s*([A-Z0-9][A-Z0-9._/\-]{1,80})", re.IGNORECASE), 0.96),
    ],
    "drawing_number": [
        (re.compile(r"(?:drawing(?:\s+number|\s+no\.?)?|dwg(?:\s+number|\s+no\.?)?)\s*[:#-]\s*([A-Z0-9][A-Z0-9._/\-]{1,80})", re.IGNORECASE), 0.95),
    ],
    "revision": [
        (re.compile(r"(?:revision|rev(?:ision)?\.?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/\-]{0,12})", re.IGNORECASE), 0.92),
    ],
    "customer_name": [
        (re.compile(r"(?:customer|oem)\s*[:#-]\s*([^\n\r]{2,100})", re.IGNORECASE), 0.88),
    ],
    "supplier_name": [
        (re.compile(r"(?:supplier|vendor|manufacturer)\s*[:#-]\s*([^\n\r]{2,100})", re.IGNORECASE), 0.88),
    ],
    "process_name": [
        (re.compile(r"(?:process(?:\s+name)?|manufacturing\s+process)\s*[:#-]\s*([^\n\r]{2,120})", re.IGNORECASE), 0.86),
    ],
    "material": [
        (re.compile(r"(?:material|matl\.?|alloy)\s*[:#-]\s*([^\n\r]{2,120})", re.IGNORECASE), 0.86),
    ],
    "submission_reason": [
        (re.compile(r"(?:submission\s+reason|reason\s+for\s+submission|reason)\s*[:#-]\s*([^\n\r]{2,140})", re.IGNORECASE), 0.84),
    ],
    "approval_status": [
        (re.compile(r"(?:approval\s+status|warrant\s+status|status)\s*[:#-]\s*([^\n\r]{2,80})", re.IGNORECASE), 0.82),
    ],
    "signatory": [
        (re.compile(r"(?:signed\s+by|approved\s+by|signatory|prepared\s+by)\s*[:#-]\s*([^\n\r]{2,100})", re.IGNORECASE), 0.82),
    ],
    "date": [
        (re.compile(r"(?:date|submission\s+date|inspection\s+date)\s*[:#-]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE), 0.8),
    ],
    "ppap_level": [
        (re.compile(r"ppap\s+level\s*[:#-]?\s*([1-5])", re.IGNORECASE), 0.9),
    ],
}

DOCUMENT_KEYWORDS: dict[DocumentType, tuple[tuple[str, float], ...]] = {
    DocumentType.PSW: (("part submission warrant", 0.95), (" psw ", 0.76), ("warrant status", 0.7)),
    DocumentType.DESIGN_RECORD: (("design record", 0.9), ("drawing number", 0.72), ("dwg", 0.66)),
    DocumentType.BALLOONED_DRAWING: (("ballooned drawing", 0.96), ("balloon", 0.72)),
    DocumentType.PFMEA: (("pfmea", 0.96), ("process failure mode", 0.92)),
    DocumentType.DFMEA: (("dfmea", 0.96), ("design failure mode", 0.92)),
    DocumentType.PROCESS_FLOW: (("process flow", 0.96), ("flow diagram", 0.84)),
    DocumentType.CONTROL_PLAN: (("control plan", 0.97),),
    DocumentType.MSA: (("measurement systems analysis", 0.94), ("gage r&r", 0.9), ("grr", 0.74)),
    DocumentType.DIMENSIONAL_RESULTS: (("dimensional results", 0.96), ("layout inspection", 0.86), ("dimensional report", 0.88)),
    DocumentType.MATERIAL_RESULTS: (("material test", 0.92), ("material results", 0.92)),
    DocumentType.PERFORMANCE_RESULTS: (("performance test", 0.92), ("performance results", 0.92)),
    DocumentType.PROCESS_STUDY: (("initial process study", 0.96), ("cpk", 0.7), ("ppk", 0.7), ("capability study", 0.88)),
    DocumentType.CUSTOMER_REQUIREMENTS: (("customer-specific requirements", 0.95), ("customer requirements", 0.88)),
    DocumentType.FAIR: (("first article inspection report", 0.98), ("fair", 0.86), ("as9102", 0.9)),
    DocumentType.MATERIAL_CERTIFICATE: (("material certificate", 0.95), ("certificate of conformance", 0.84), ("mill cert", 0.86)),
    DocumentType.SPECIAL_PROCESS_CERTIFICATE: (("special process certificate", 0.95), ("nadcap", 0.82)),
    DocumentType.MEASUREMENT_TRACEABILITY: (("measurement traceability", 0.94), ("calibration certificate", 0.84)),
}

SPECIAL_TOKENS = ("<sc>", "special", "critical", "key characteristic", "cc")
PASS_TOKENS = {"pass", "ok", "accept", "accepted", "conform", "true"}
FAIL_TOKENS = {"fail", "reject", "rejected", "ng", "nonconforming", "false"}

HEADER_SYNONYMS: dict[str, tuple[str, ...]] = {
    "characteristic_id": ("characteristic id", "char id", "feature id", "item", "feature", "characteristic"),
    "balloon_number": ("balloon", "balloon number", "balloon no", "item no", "bubble"),
    "description": ("description", "characteristic description", "feature description"),
    "nominal": ("nominal", "target", "spec", "basic dimension"),
    "tolerance": ("tolerance", "tol", "+/-"),
    "unit": ("unit", "units"),
    "measured_value": ("measured", "actual", "measurement", "result value", "measured value"),
    "result": ("result", "status", "pass/fail", "accept/reject"),
    "step_id": ("step", "process step", "operation", "op", "op no", "sequence"),
    "step_name": ("step name", "operation description", "process step name", "process"),
    "control_method": ("control method", "inspection method", "method"),
    "reaction_plan": ("reaction plan", "reaction"),
    "failure_mode": ("failure mode", "mode of failure"),
    "severity": ("severity", "sev"),
    "risk_priority": ("rpn", "risk priority", "risk priority number"),
    "certificate_type": ("certificate", "cert type", "document"),
    "identifier": ("identifier", "certificate id", "cert no", "number"),
}


class UploadSubmissionBuilder:
    def build(
        self,
        files: list[tuple[str, bytes]],
        context: SubmissionContext,
    ) -> UploadBuildResult:
        warnings: list[str] = []
        documents: list[DocumentRecord] = []
        for file_name, payload in files:
            parsed = self._parse_document(file_name, payload)
            documents.append(parsed.document)
            warnings.extend(parsed.warnings)

        hydrated_context = self._hydrate_context(context, documents)
        package = SubmissionPackage(
            submission_id=self._submission_id(),
            submission_mode=hydrated_context.requested_submission_mode
            if hydrated_context.requested_submission_mode != SubmissionMode.UNKNOWN
            else SubmissionMode.UNKNOWN,
            context=hydrated_context,
            documents=documents,
        )
        return UploadBuildResult(package=package, warnings=warnings)

    def _parse_document(self, file_name: str, payload: bytes) -> ParsedUploadDocument:
        suffix = Path(file_name).suffix.lower()
        warnings: list[str] = []
        try:
            fragments, tables = self._extract_content(file_name, payload, suffix)
        except Exception as exc:
            warning = f"{file_name}: parser failed ({exc}). Manual review is required."
            return ParsedUploadDocument(
                document=DocumentRecord(
                    file_name=file_name,
                    document_type=DocumentType.UNKNOWN,
                    classification_confidence=0.25,
                    notes=[
                        "File parsing failed, so no verifiable machine extraction is available for this document.",
                    ],
                ),
                warnings=[warning],
            )
        joined_text = "\n".join(fragment.text for fragment in fragments if fragment.text).strip()

        document_type, classification_confidence = self._classify_document(file_name, joined_text)
        metadata = self._extract_metadata(file_name, fragments)
        metadata = self._merge_filename_inference(file_name, metadata)
        structured = self._extract_structured_rows(file_name, document_type, tables)

        notes: list[str] = []
        if suffix == ".pdf" and len(joined_text) < 80:
            notes.append(
                "No reliable machine-readable PDF text was extracted. Scanned or image-based pages require OCR or manual review."
            )
            warnings.append(f"{file_name}: PDF appears image-based or text-poor; OCR is not enabled yet.")
        if document_type == DocumentType.UNKNOWN:
            notes.append(
                "Document type could not be classified confidently from file content. Validation coverage may be incomplete."
            )
        if suffix not in {".pdf", ".txt", ".csv", ".tsv", ".xlsx", ".xlsm", ".json"}:
            notes.append(
                "File type is not fully supported by the parser in this release. Only filename-based and low-confidence extraction may be available."
            )
            warnings.append(f"{file_name}: unsupported file type; parser coverage is limited.")

        document = DocumentRecord(
            file_name=file_name,
            document_type=document_type,
            classification_confidence=classification_confidence,
            metadata=metadata,
            drawing_characteristics=structured["drawing_characteristics"],
            inspection_results=structured["inspection_results"],
            process_flow_steps=structured["process_flow_steps"],
            pfmea_entries=structured["pfmea_entries"],
            control_plan_entries=structured["control_plan_entries"],
            certificates=structured["certificates"],
            notes=notes,
        )
        return ParsedUploadDocument(document=document, warnings=warnings)

    def _extract_content(
        self,
        file_name: str,
        payload: bytes,
        suffix: str,
    ) -> tuple[list[TextFragment], list[TableSection]]:
        if suffix == ".pdf":
            return self._extract_pdf(payload), []
        if suffix in {".txt", ".md"}:
            text = payload.decode("utf-8", errors="ignore")
            return [TextFragment(text=text, section_name="text")], []
        if suffix in {".csv", ".tsv"}:
            dialect = csv.excel_tab if suffix == ".tsv" else csv.excel
            text = payload.decode("utf-8", errors="ignore")
            rows = list(csv.reader(io.StringIO(text), dialect=dialect))
            table = TableSection(section_name="table", rows=[[self._clean_cell(cell) for cell in row] for row in rows])
            fragments = [TextFragment(text="\n".join(" | ".join(filter(None, row)) for row in table.rows), section_name="table")]
            return fragments, [table]
        if suffix in {".xlsx", ".xlsm"}:
            return self._extract_workbook(payload)
        if suffix == ".json":
            text = payload.decode("utf-8", errors="ignore")
            try:
                pretty = json.dumps(json.loads(text), ensure_ascii=True, indent=2)
            except json.JSONDecodeError:
                pretty = text
            return [TextFragment(text=pretty, section_name="json")], []
        return [TextFragment(text="", section_name="unsupported")], []

    def _extract_pdf(self, payload: bytes) -> list[TextFragment]:
        reader = PdfReader(io.BytesIO(payload))
        fragments: list[TextFragment] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            fragments.append(TextFragment(text=text, page_number=index))
        return fragments

    def _extract_workbook(self, payload: bytes) -> tuple[list[TextFragment], list[TableSection]]:
        workbook = load_workbook(io.BytesIO(payload), data_only=True, read_only=True)
        fragments: list[TextFragment] = []
        tables: list[TableSection] = []
        for worksheet in workbook.worksheets:
            rows: list[list[str]] = []
            line_buffer: list[str] = []
            for row in worksheet.iter_rows(values_only=True):
                cleaned = [self._clean_cell(cell) for cell in row]
                if not any(cleaned):
                    continue
                rows.append(cleaned)
                line_buffer.append(" | ".join(cell for cell in cleaned if cell))
            if not rows:
                continue
            tables.append(TableSection(section_name=worksheet.title, rows=rows))
            fragments.append(TextFragment(text="\n".join(line_buffer), section_name=worksheet.title))
        return fragments, tables

    def _classify_document(
        self,
        file_name: str,
        text: str,
    ) -> tuple[DocumentType, float]:
        haystack = self._normalized_haystack(file_name, text)
        best_type = DocumentType.UNKNOWN
        best_signal_score = 0.0
        best_confidence = 0.28
        for document_type, keywords in DOCUMENT_KEYWORDS.items():
            score = 0.0
            hits = 0
            for token, weight in keywords:
                if self._normalized_token(token) in haystack:
                    score += weight
                    hits += 1
            if score > best_signal_score:
                best_type = document_type
                best_signal_score = score
                best_confidence = min(0.98, 0.45 + min(score, 1.6) / 2 + hits * 0.03)
        return best_type, round(best_confidence, 2)

    def _extract_metadata(
        self,
        file_name: str,
        fragments: list[TextFragment],
    ) -> dict[str, ExtractedValue]:
        metadata: dict[str, ExtractedValue] = {}
        for field_name, patterns in FIELD_PATTERNS.items():
            extracted = self._search_patterns(file_name, fragments, field_name, patterns)
            if extracted is not None:
                metadata[field_name] = extracted
        return metadata

    def _search_patterns(
        self,
        file_name: str,
        fragments: list[TextFragment],
        field_name: str,
        patterns: list[tuple[re.Pattern[str], float]],
    ) -> ExtractedValue | None:
        for fragment in fragments:
            for pattern, confidence in patterns:
                match = pattern.search(fragment.text)
                if not match:
                    continue
                value = self._normalize_capture(match.group(1))
                if not value:
                    continue
                snippet = self._match_snippet(fragment.text, match.span(1))
                evidence = EvidenceRef(
                    file_name=file_name,
                    page_number=fragment.page_number,
                    section_name=fragment.section_name,
                    field_name=field_name,
                    snippet=snippet,
                    confidence=confidence,
                )
                return ExtractedValue(
                    value=value,
                    status=ExtractionStatus.VERIFIED,
                    confidence=confidence,
                    evidence=[evidence],
                )
        return None

    def _merge_filename_inference(
        self,
        file_name: str,
        metadata: dict[str, ExtractedValue],
    ) -> dict[str, ExtractedValue]:
        stem = Path(file_name).stem
        if "revision" not in metadata:
            revision_match = re.search(r"(?:^|[_\-])rev(?:ision)?[_\-]?([A-Z0-9]{1,6})(?:$|[_\-])", stem, re.IGNORECASE)
            if revision_match:
                metadata["revision"] = self._low_confidence_filename_value(
                    file_name, "revision", revision_match.group(1).upper(), 0.58
                )

        if "part_number" not in metadata:
            tokens = [token for token in re.split(r"[_\s]+", stem) if token]
            for token in tokens:
                if re.fullmatch(r"[A-Z0-9][A-Z0-9\-]{3,40}", token, re.IGNORECASE):
                    metadata["part_number"] = self._low_confidence_filename_value(
                        file_name, "part_number", token, 0.5
                    )
                    break

        return metadata

    def _low_confidence_filename_value(
        self,
        file_name: str,
        field_name: str,
        value: str,
        confidence: float,
    ) -> ExtractedValue:
        return ExtractedValue(
            value=value,
            status=ExtractionStatus.INFERRED_LOW_CONFIDENCE,
            confidence=confidence,
            evidence=[
                EvidenceRef(
                    file_name=file_name,
                    field_name=field_name,
                    snippet=f"Inferred from file name: {file_name}",
                    confidence=confidence,
                )
            ],
        )

    def _extract_structured_rows(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> dict[str, list]:
        return {
            "drawing_characteristics": self._parse_drawing_characteristics(file_name, document_type, sections),
            "inspection_results": self._parse_inspection_results(file_name, document_type, sections),
            "process_flow_steps": self._parse_process_flow_steps(file_name, document_type, sections),
            "pfmea_entries": self._parse_pfmea_entries(file_name, document_type, sections),
            "control_plan_entries": self._parse_control_plan_entries(file_name, document_type, sections),
            "certificates": self._parse_certificates(file_name, document_type, sections),
        }

    def _parse_drawing_characteristics(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> list[DrawingCharacteristic]:
        if document_type not in {
            DocumentType.DESIGN_RECORD,
            DocumentType.BALLOONED_DRAWING,
            DocumentType.FAIR,
            DocumentType.DIMENSIONAL_RESULTS,
        }:
            return []
        characteristics: list[DrawingCharacteristic] = []
        for section in sections:
            header_row, mapping = self._find_header(section.rows, {"description", "nominal", "tolerance"})
            if header_row is None or not (mapping.get("characteristic_id") or mapping.get("balloon_number")):
                continue
            for row in section.rows[header_row + 1 :]:
                if not any(row):
                    continue
                characteristic_id = self._value_from_row(row, mapping, "characteristic_id") or self._value_from_row(
                    row, mapping, "balloon_number"
                )
                balloon_number = self._value_from_row(row, mapping, "balloon_number") or characteristic_id
                description = self._value_from_row(row, mapping, "description")
                if not characteristic_id or not description:
                    continue
                characteristic_type = CharacteristicType.STANDARD
                if any(token in description.lower() for token in SPECIAL_TOKENS):
                    characteristic_type = CharacteristicType.SPECIAL
                characteristics.append(
                    DrawingCharacteristic(
                        characteristic_id=characteristic_id,
                        balloon_number=balloon_number,
                        description=description,
                        nominal=self._value_from_row(row, mapping, "nominal"),
                        tolerance=self._value_from_row(row, mapping, "tolerance"),
                        unit=self._value_from_row(row, mapping, "unit"),
                        characteristic_type=characteristic_type,
                        source_document=file_name,
                        evidence=[self._row_evidence(file_name, section.section_name, "characteristic", row, 0.86)],
                    )
                )
        return characteristics

    def _parse_inspection_results(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> list[InspectionResult]:
        if document_type not in {DocumentType.DIMENSIONAL_RESULTS, DocumentType.FAIR}:
            return []
        results: list[InspectionResult] = []
        for section in sections:
            header_row, mapping = self._find_header(section.rows, {"measured_value"})
            if header_row is None or not (mapping.get("characteristic_id") or mapping.get("balloon_number")):
                continue
            for row in section.rows[header_row + 1 :]:
                if not any(row):
                    continue
                characteristic_id = self._value_from_row(row, mapping, "characteristic_id") or self._value_from_row(
                    row, mapping, "balloon_number"
                )
                balloon_number = self._value_from_row(row, mapping, "balloon_number")
                measured_value = self._value_from_row(row, mapping, "measured_value")
                if not characteristic_id and not balloon_number:
                    continue
                if not measured_value:
                    continue
                results.append(
                    InspectionResult(
                        characteristic_id=characteristic_id,
                        balloon_number=balloon_number,
                        measured_value=measured_value,
                        unit=self._value_from_row(row, mapping, "unit"),
                        result=self._measurement_status(self._value_from_row(row, mapping, "result")),
                        source_document=file_name,
                        evidence=[self._row_evidence(file_name, section.section_name, "measurement", row, 0.88)],
                    )
                )
        return results

    def _parse_process_flow_steps(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> list[ProcessFlowStep]:
        if document_type != DocumentType.PROCESS_FLOW:
            return []
        steps: list[ProcessFlowStep] = []
        for section in sections:
            header_row, mapping = self._find_header(section.rows, {"step_id"})
            if header_row is None:
                continue
            for sequence, row in enumerate(section.rows[header_row + 1 :], start=1):
                step_id = self._value_from_row(row, mapping, "step_id")
                if not step_id:
                    continue
                steps.append(
                    ProcessFlowStep(
                        step_id=step_id,
                        step_name=self._value_from_row(row, mapping, "step_name") or step_id,
                        sequence=sequence,
                        evidence=[self._row_evidence(file_name, section.section_name, "process_step", row, 0.84)],
                    )
                )
        return steps

    def _parse_pfmea_entries(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> list[PfmeaEntry]:
        if document_type != DocumentType.PFMEA:
            return []
        entries: list[PfmeaEntry] = []
        for section in sections:
            header_row, mapping = self._find_header(section.rows, {"step_id", "failure_mode"})
            if header_row is None:
                continue
            for row in section.rows[header_row + 1 :]:
                step_id = self._value_from_row(row, mapping, "step_id")
                failure_mode = self._value_from_row(row, mapping, "failure_mode")
                if not step_id or not failure_mode:
                    continue
                entries.append(
                    PfmeaEntry(
                        step_id=step_id,
                        failure_mode=failure_mode,
                        severity_rating=self._to_int(self._value_from_row(row, mapping, "severity")),
                        risk_priority=self._to_int(self._value_from_row(row, mapping, "risk_priority")),
                        evidence=[self._row_evidence(file_name, section.section_name, "pfmea", row, 0.82)],
                    )
                )
        return entries

    def _parse_control_plan_entries(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> list[ControlPlanEntry]:
        if document_type != DocumentType.CONTROL_PLAN:
            return []
        entries: list[ControlPlanEntry] = []
        for section in sections:
            header_row, mapping = self._find_header(section.rows, {"step_id"})
            if header_row is None or "control_method" not in mapping:
                continue
            for row in section.rows[header_row + 1 :]:
                step_id = self._value_from_row(row, mapping, "step_id")
                if not step_id:
                    continue
                characteristic_value = (
                    self._value_from_row(row, mapping, "characteristic_id")
                    or self._value_from_row(row, mapping, "balloon_number")
                    or ""
                )
                characteristic_ids = [item.strip() for item in re.split(r"[,;/]", characteristic_value) if item.strip()]
                entries.append(
                    ControlPlanEntry(
                        step_id=step_id,
                        characteristic_ids=characteristic_ids,
                        control_method=self._value_from_row(row, mapping, "control_method"),
                        reaction_plan=self._value_from_row(row, mapping, "reaction_plan"),
                        evidence=[self._row_evidence(file_name, section.section_name, "control_plan", row, 0.82)],
                    )
                )
        return entries

    def _parse_certificates(
        self,
        file_name: str,
        document_type: DocumentType,
        sections: list[TableSection],
    ) -> list[CertificateRecord]:
        if document_type not in {
            DocumentType.MATERIAL_CERTIFICATE,
            DocumentType.SPECIAL_PROCESS_CERTIFICATE,
            DocumentType.MATERIAL_RESULTS,
        }:
            return []
        records: list[CertificateRecord] = []
        for section in sections:
            header_row, mapping = self._find_header(section.rows, {"identifier"})
            if header_row is None:
                continue
            for row in section.rows[header_row + 1 :]:
                identifier = self._value_from_row(row, mapping, "identifier")
                if not identifier:
                    continue
                records.append(
                    CertificateRecord(
                        certificate_type=self._value_from_row(row, mapping, "certificate_type") or document_type.value,
                        identifier=identifier,
                        source_document=file_name,
                        evidence=[self._row_evidence(file_name, section.section_name, "certificate", row, 0.8)],
                    )
                )
        return records

    def _find_header(
        self,
        rows: list[list[str]],
        required_fields: set[str],
    ) -> tuple[int | None, dict[str, int]]:
        for index, row in enumerate(rows[:25]):
            mapping = self._header_mapping(row)
            if required_fields.issubset(mapping.keys()):
                return index, mapping
        return None, {}

    def _header_mapping(self, row: list[str]) -> dict[str, int]:
        mapping: dict[str, int] = {}
        for index, cell in enumerate(row):
            normalized = self._normalize_header(cell)
            if not normalized:
                continue
            for canonical, aliases in HEADER_SYNONYMS.items():
                if canonical in mapping:
                    continue
                if normalized == canonical or normalized in aliases:
                    mapping[canonical] = index
                    break
        return mapping

    def _value_from_row(
        self,
        row: list[str],
        mapping: dict[str, int],
        field_name: str,
    ) -> str | None:
        index = mapping.get(field_name)
        if index is None or index >= len(row):
            return None
        value = self._clean_cell(row[index])
        return value or None

    def _hydrate_context(
        self,
        context: SubmissionContext,
        documents: Iterable[DocumentRecord],
    ) -> SubmissionContext:
        updates: dict[str, object] = {}
        if context.ppap_level is None:
            for document in documents:
                field = document.metadata.get("ppap_level")
                if field and field.is_present and field.text.isdigit():
                    updates["ppap_level"] = int(field.text)
                    break

        for context_key, metadata_key in (
            ("part_number", "part_number"),
            ("drawing_number", "drawing_number"),
            ("revision", "revision"),
            ("customer_oem", "customer_name"),
            ("supplier_name", "supplier_name"),
            ("manufacturing_process", "process_name"),
            ("material", "material"),
        ):
            if getattr(context, context_key):
                continue
            for document in documents:
                field = document.metadata.get(metadata_key)
                if field and field.is_present:
                    updates[context_key] = field.text
                    break

        return context.model_copy(update=updates)

    def _submission_id(self) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"upload-{timestamp}-{uuid.uuid4().hex[:8]}"

    def _measurement_status(self, value: str | None) -> MeasurementStatus:
        if not value:
            return MeasurementStatus.UNCLEAR
        normalized = value.strip().lower()
        if normalized in PASS_TOKENS:
            return MeasurementStatus.PASS
        if normalized in FAIL_TOKENS:
            return MeasurementStatus.FAIL
        return MeasurementStatus.UNCLEAR

    def _normalize_capture(self, value: str) -> str:
        value = re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip(" :;-")
        return value

    def _normalized_haystack(self, file_name: str, text: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", f"{file_name} {text}".lower())
        return f" {normalized.strip()} "

    def _normalized_token(self, token: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", token.lower()).strip()
        return f" {normalized} "

    def _match_snippet(self, text: str, span: tuple[int, int]) -> str:
        start, end = span
        left = max(0, start - 40)
        right = min(len(text), end + 60)
        return self._normalize_capture(text[left:right])

    def _clean_cell(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        return str(value).strip()

    def _normalize_header(self, value: str) -> str:
        value = self._clean_cell(value).lower()
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    def _to_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        match = re.search(r"-?\d+", value)
        if not match:
            return None
        return int(match.group(0))

    def _row_evidence(
        self,
        file_name: str,
        section_name: str,
        field_name: str,
        row: list[str],
        confidence: float,
    ) -> EvidenceRef:
        return EvidenceRef(
            file_name=file_name,
            section_name=section_name,
            field_name=field_name,
            snippet=" | ".join(cell for cell in row if cell)[:220],
            confidence=confidence,
        )
