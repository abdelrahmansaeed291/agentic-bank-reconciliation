from uuid import uuid4

from .graph import ReconciliationGraph
from .models import (
    ApprovalStatus,
    AuditEvent,
    CaseRecord,
    CaseStatus,
    DecisionRequest,
)
from .repository import CaseRepository
from .tools import BankingClient


class CaseNotFoundError(KeyError):
    pass


class InvalidCaseStateError(RuntimeError):
    pass


class ReconciliationCaseService:
    def __init__(
        self,
        graph: ReconciliationGraph,
        banking: BankingClient,
        repository: CaseRepository,
    ) -> None:
        self.graph = graph
        self.banking = banking
        self.repository = repository

    async def investigate(self, transaction_id: str) -> CaseRecord:
        state = await self.graph.investigate(transaction_id)
        case = CaseRecord(
            case_id=str(uuid4()),
            transaction_id=transaction_id,
            transaction=state["transaction"],
            invoice=state.get("invoice"),
            difference=state["difference"],
            policy_evidence=state["policy_evidence"],
            recommended_action=state["recommended_action"],
            tool_trace=state["tool_trace"],
            audit_trail=[
                AuditEvent(
                    event="INVESTIGATION_COMPLETED",
                    details={
                        "tools_called": [item.tool for item in state["tool_trace"]],
                        "recommended_action": state["recommended_action"].action,
                        "approval_status": ApprovalStatus.PENDING,
                        "final_status": CaseStatus.WAITING_FOR_APPROVAL,
                    },
                )
            ],
        )
        return self.repository.save(case)

    def get(self, case_id: str) -> CaseRecord:
        case = self.repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        return case

    async def approve(self, case_id: str, decision: DecisionRequest) -> CaseRecord:
        case = self.get(case_id)
        if case.final_status != CaseStatus.WAITING_FOR_APPROVAL:
            raise InvalidCaseStateError(f"Case is already {case.final_status}")
        case.approval_status = ApprovalStatus.APPROVED
        case.audit_trail.append(
            AuditEvent(
                event="HUMAN_APPROVED",
                details={"decided_by": decision.decided_by, "reason": decision.reason},
            )
        )
        self.repository.save(case)
        try:
            result = await self.banking.resolve_transaction(
                case.transaction_id, case.case_id, case.recommended_action.action
            )
        except Exception as exc:
            case.final_status = CaseStatus.EXECUTION_FAILED
            case.audit_trail.append(
                AuditEvent(event="ACTION_FAILED", details={"error": str(exc)})
            )
            self.repository.save(case)
            raise
        case.final_status = CaseStatus.RESOLVED
        case.transaction.status = result["transaction"]["status"]
        case.transaction.resolution_action = result["transaction"].get("resolution_action")
        case.audit_trail.append(
            AuditEvent(
                event="ACTION_EXECUTED",
                details={
                    "executed_action": case.recommended_action.action,
                    "final_status": CaseStatus.RESOLVED,
                },
            )
        )
        return self.repository.save(case)

    def reject(self, case_id: str, decision: DecisionRequest) -> CaseRecord:
        case = self.get(case_id)
        if case.final_status != CaseStatus.WAITING_FOR_APPROVAL:
            raise InvalidCaseStateError(f"Case is already {case.final_status}")
        case.approval_status = ApprovalStatus.REJECTED
        case.final_status = CaseStatus.REJECTED
        case.audit_trail.append(
            AuditEvent(
                event="HUMAN_REJECTED",
                details={
                    "decided_by": decision.decided_by,
                    "reason": decision.reason,
                    "final_status": CaseStatus.REJECTED,
                },
            )
        )
        return self.repository.save(case)
