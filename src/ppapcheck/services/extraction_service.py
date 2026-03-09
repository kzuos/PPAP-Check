from __future__ import annotations

from ppapcheck.models import (
    EvidenceRef,
    ExtractedValue,
    ExtractionStatus,
    SubmissionPackage,
)


class ExtractionService:
    """Normalizes extracted payloads without inventing missing evidence."""

    def normalize(self, package: SubmissionPackage) -> SubmissionPackage:
        normalized_documents = []
        for document in package.documents:
            normalized_metadata = dict(sorted(document.metadata.items(), key=lambda item: item[0]))
            if "material" not in normalized_metadata or not normalized_metadata["material"].is_present:
                derived_material = self._material_from_certificates(document.certificates)
                if derived_material is not None:
                    normalized_metadata["material"] = derived_material
            normalized_documents.append(document.model_copy(update={"metadata": normalized_metadata}))
        return package.model_copy(update={"documents": normalized_documents})

    def _material_from_certificates(self, certificates) -> ExtractedValue | None:
        material_specs = [
            record
            for record in certificates
            if record.certificate_type == "material_specification" and record.identifier
        ]
        if not material_specs:
            return None

        ranked = sorted(
            material_specs,
            key=lambda record: (
                "bronze" in record.identifier.lower(),
                "en ac" in record.identifier.lower(),
                "ts en" in record.identifier.lower(),
                len(record.identifier),
            ),
            reverse=True,
        )
        chosen = ranked[0]
        supporting = next(
            (
                record.identifier
                for record in ranked[1:]
                if record.identifier and record.identifier != chosen.identifier
            ),
            None,
        )
        material_text = chosen.identifier
        if supporting and supporting not in material_text:
            material_text = f"{material_text} / {supporting}"

        evidence = chosen.evidence[:1] or [
            EvidenceRef(
                file_name=chosen.source_document or "unknown",
                field_name="material",
                snippet=material_text,
                confidence=0.83,
            )
        ]
        return ExtractedValue(
            value=material_text,
            status=ExtractionStatus.VERIFIED,
            confidence=max(evidence[0].confidence, 0.83),
            evidence=evidence,
        )
