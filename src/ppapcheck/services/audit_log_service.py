from __future__ import annotations

from collections import defaultdict

from ppapcheck.models import AuditLogEntry


class AuditLogService:
    def __init__(self) -> None:
        self._entries: dict[str, list[AuditLogEntry]] = defaultdict(list)

    def record(self, submission_id: str, stage: str, message: str, **details: object) -> None:
        self._entries[submission_id].append(
            AuditLogEntry(stage=stage, message=message, details=dict(details))
        )

    def get_entries(self, submission_id: str) -> list[AuditLogEntry]:
        return list(self._entries.get(submission_id, []))

