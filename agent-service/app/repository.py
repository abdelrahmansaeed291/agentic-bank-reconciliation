from threading import Lock

from .models import CaseRecord, utc_now


class CaseRepository:
    """Thread-safe in-memory case store suitable for a single demo process."""

    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}
        self._lock = Lock()

    def save(self, case: CaseRecord) -> CaseRecord:
        with self._lock:
            case.updated_at = utc_now()
            self._cases[case.case_id] = case.model_copy(deep=True)
            return case.model_copy(deep=True)

    def get(self, case_id: str) -> CaseRecord | None:
        with self._lock:
            case = self._cases.get(case_id)
            return case.model_copy(deep=True) if case else None
