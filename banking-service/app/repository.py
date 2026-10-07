import json
from pathlib import Path
from threading import Lock

from .models import Invoice, Transaction, TransactionStatus


class BankingRepository:
    """Small thread-safe in-memory repository loaded from synthetic JSON data."""

    def __init__(self, data_dir: Path) -> None:
        self._lock = Lock()
        self._transactions = {
            item["transaction_id"]: Transaction.model_validate(item)
            for item in self._load(data_dir / "transactions.json")
        }
        self._invoices = {
            item["invoice_reference"]: Invoice.model_validate(item)
            for item in self._load(data_dir / "invoices.json")
        }

    @staticmethod
    def _load(path: Path) -> list[dict]:
        return json.loads(path.read_text(encoding="utf-8"))

    def list_transactions(self) -> list[Transaction]:
        return [item.model_copy(deep=True) for item in self._transactions.values()]

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        item = self._transactions.get(transaction_id)
        return item.model_copy(deep=True) if item else None

    def get_invoice(self, invoice_reference: str) -> Invoice | None:
        item = self._invoices.get(invoice_reference)
        return item.model_copy(deep=True) if item else None

    def resolve(self, transaction_id: str, action: str) -> Transaction | None:
        with self._lock:
            item = self._transactions.get(transaction_id)
            if item is None:
                return None
            item.status = TransactionStatus.RESOLVED
            item.resolution_action = action
            return item.model_copy(deep=True)
