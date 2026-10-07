from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseStatus(StrEnum):
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Transaction(BaseModel):
    transaction_id: str
    amount: float
    currency: str
    reference: str | None = None
    counterparty: str
    status: str
    resolution_action: str | None = None


class Invoice(BaseModel):
    invoice_reference: str
    expected_amount: float
    currency: str
    customer: str


class Difference(BaseModel):
    expected_amount: float | None
    received_amount: float
    amount_difference: float | None
    currency_match: bool | None


class PolicyEvidence(BaseModel):
    section: str
    text: str
    score: float = Field(ge=0, le=1)


class Recommendation(BaseModel):
    action: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    requires_approval: bool = True


class ToolTraceEntry(BaseModel):
    tool: str
    summary: str
    success: bool = True


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    event: str
    details: dict[str, Any] = Field(default_factory=dict)


class CaseRecord(BaseModel):
    case_id: str
    transaction_id: str
    transaction: Transaction
    invoice: Invoice | None = None
    difference: Difference
    policy_evidence: list[PolicyEvidence]
    recommended_action: Recommendation
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    final_status: CaseStatus = CaseStatus.WAITING_FOR_APPROVAL
    tool_trace: list[ToolTraceEntry]
    audit_trail: list[AuditEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InvestigateRequest(BaseModel):
    transaction_id: str = Field(min_length=1)


class DecisionRequest(BaseModel):
    decided_by: str = Field(default="interview-demo-user", min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=500)
