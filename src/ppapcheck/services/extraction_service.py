from __future__ import annotations

from ppapcheck.models import SubmissionPackage


class ExtractionService:
    """Normalizes extracted payloads without inventing missing evidence."""

    def normalize(self, package: SubmissionPackage) -> SubmissionPackage:
        normalized_documents = []
        for document in package.documents:
            normalized_metadata = dict(sorted(document.metadata.items(), key=lambda item: item[0]))
            normalized_documents.append(document.model_copy(update={"metadata": normalized_metadata}))
        return package.model_copy(update={"documents": normalized_documents})

