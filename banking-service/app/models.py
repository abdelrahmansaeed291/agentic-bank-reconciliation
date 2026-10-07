from enum import StrEnum

from pydantic import BaseModel, Field


class TransactionStatus(StrEnum):
    UNRECONCILED = "UNRECONCILED"
    RESOLVED = "RESOLVED"


class Transaction(BaseModel):
    transaction_id: str
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    reference: str | None = None
    counterparty: str
    status: TransactionStatus = TransactionStatus.UNRECONCILED
    resolution_action: str | None = None


class Invoice(BaseModel):
    invoice_reference: str
    expected_amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    customer: str


class ResolveRequest(BaseModel):
    case_id: str
    action: str
    approval_status: str


class ResolveResponse(BaseModel):
    transaction: Transaction
    message: str
