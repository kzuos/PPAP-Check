from __future__ import annotations

from ppapcheck.models import DOCUMENT_TYPE_ALIASES, DocumentRecord, DocumentType


class DocumentClassifier:
    def classify(self, document: DocumentRecord) -> DocumentRecord:
        if document.document_type != DocumentType.UNKNOWN:
            return document

        name = document.file_name.lower()
        for hint, document_type in DOCUMENT_TYPE_ALIASES.items():
            if hint in name:
                return document.model_copy(
                    update={
                        "document_type": document_type,
                        "classification_confidence": min(document.classification_confidence, 0.72),
                    }
                )

        return document

    def classify_all(self, documents: list[DocumentRecord]) -> list[DocumentRecord]:
        return [self.classify(document) for document in documents]

