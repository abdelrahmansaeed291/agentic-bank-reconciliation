from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from .models import Invoice, ResolveRequest, ResolveResponse, Transaction
from .repository import BankingRepository

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALLOWED_ACTIONS = {
    "MARK_RECONCILED",
    "ACCEPT_MINOR_DISCREPANCY",
    "MANUAL_REFERENCE_REVIEW",
    "INVESTIGATE_CURRENCY_MISMATCH",
    "INVESTIGATE_UNKNOWN_INVOICE",
}

app = FastAPI(
    title="Mock Banking Service",
    version="1.0.0",
    description="Synthetic read/write boundary for the reconciliation demo.",
)
app.state.repository = BankingRepository(DATA_DIR)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "banking-service"}


@app.get("/transactions", response_model=list[Transaction])
def list_transactions() -> list[Transaction]:
    return app.state.repository.list_transactions()


@app.get("/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: str) -> Transaction:
    transaction = app.state.repository.get_transaction(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@app.get("/invoices/{invoice_reference}", response_model=Invoice)
def get_invoice(invoice_reference: str) -> Invoice:
    invoice = app.state.repository.get_invoice(invoice_reference)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.post("/transactions/{transaction_id}/resolve", response_model=ResolveResponse)
def resolve_transaction(transaction_id: str, request: ResolveRequest) -> ResolveResponse:
    if request.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explicit human approval is required",
        )
    if request.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=422, detail="Unsupported resolution action")
    transaction = app.state.repository.resolve(transaction_id, request.action)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return ResolveResponse(transaction=transaction, message="Approved action executed")
