import json
from pathlib import Path

import httpx
import pytest

from app.graph import ReconciliationGraph
from app.llm import DemoRecommendationProvider
from app.models import CaseStatus, DecisionRequest
from app.rag import PolicyRetriever
from app.repository import CaseRepository
from app.service import ReconciliationCaseService
from app.tools import BankingClient


POLICY = Path(__file__).resolve().parents[2] / "policies" / "reconciliation_policy.md"


def mock_banking(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/transactions/TX1003":
        return httpx.Response(
            200,
            json={
                "transaction_id": "TX1003",
                "amount": 980,
                "currency": "EUR",
                "reference": "INV-1003",
                "counterparty": "Cedar Works",
                "status": "UNRECONCILED",
            },
        )
    if request.method == "GET" and request.url.path == "/invoices/INV-1003":
        return httpx.Response(
            200,
            json={
                "invoice_reference": "INV-1003",
                "expected_amount": 1000,
                "currency": "EUR",
                "customer": "Cedar Works",
            },
        )
    if request.method == "POST" and request.url.path == "/transactions/TX1003/resolve":
        payload = json.loads(request.content)
        assert payload["approval_status"] == "APPROVED"
        return httpx.Response(
            200,
            json={
                "transaction": {
                    "transaction_id": "TX1003",
                    "amount": 980,
                    "currency": "EUR",
                    "reference": "INV-1003",
                    "counterparty": "Cedar Works",
                    "status": "RESOLVED",
                    "resolution_action": payload["action"],
                },
                "message": "Approved action executed",
            },
        )
    return httpx.Response(404)


def make_service() -> ReconciliationCaseService:
    banking = BankingClient("http://banking.test", httpx.MockTransport(mock_banking))
    graph = ReconciliationGraph(
        banking, PolicyRetriever(POLICY), DemoRecommendationProvider()
    )
    return ReconciliationCaseService(graph, banking, CaseRepository())


@pytest.mark.asyncio
async def test_investigation_pauses_before_resolution() -> None:
    case = await make_service().investigate("TX1003")
    assert case.difference.amount_difference == 20
    assert case.recommended_action.action == "ACCEPT_MINOR_DISCREPANCY"
    assert case.final_status == CaseStatus.WAITING_FOR_APPROVAL
    assert [item.tool for item in case.tool_trace] == [
        "get_transaction",
        "get_invoice",
        "calculate_difference",
        "search_policy",
        "recommend_resolution",
    ]


@pytest.mark.asyncio
async def test_only_approval_executes_resolution() -> None:
    service = make_service()
    case = await service.investigate("TX1003")
    resolved = await service.approve(case.case_id, DecisionRequest(decided_by="reviewer"))
    assert resolved.final_status == CaseStatus.RESOLVED
    assert resolved.transaction.status == "RESOLVED"
    assert resolved.audit_trail[-1].event == "ACTION_EXECUTED"


@pytest.mark.asyncio
async def test_rejection_does_not_execute_resolution() -> None:
    service = make_service()
    case = await service.investigate("TX1003")
    rejected = service.reject(case.case_id, DecisionRequest(reason="Needs evidence"))
    assert rejected.final_status == CaseStatus.REJECTED
    assert rejected.transaction.status == "UNRECONCILED"
