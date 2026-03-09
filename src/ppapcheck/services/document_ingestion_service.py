from __future__ import annotations

from ppapcheck.models import SubmissionPackage


class DocumentIngestionService:
    def ingest(self, package: SubmissionPackage) -> SubmissionPackage:
        normalized_documents = []
        for index, document in enumerate(package.documents, start=1):
            if document.document_id:
                normalized_documents.append(document)
                continue
            normalized_documents.append(
                document.model_copy(update={"document_id": f"{package.submission_id}-doc-{index}"})
            )
        return package.model_copy(update={"documents": normalized_documents})

