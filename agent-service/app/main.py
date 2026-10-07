from fastapi import FastAPI, HTTPException

from .config import settings
from .graph import ReconciliationGraph
from .llm import create_provider
from .models import AuditEvent, CaseRecord, DecisionRequest, InvestigateRequest
from .rag import PolicyRetriever
from .repository import CaseRepository
from .service import CaseNotFoundError, InvalidCaseStateError, ReconciliationCaseService
from .tools import BankingClient, BankingServiceError


def build_service() -> ReconciliationCaseService:
    banking = BankingClient(settings.banking_service_url)
    graph = ReconciliationGraph(
        banking=banking,
        retriever=PolicyRetriever(settings.policy_path),
        provider=create_provider(
            settings.llm_provider, settings.aws_region, settings.bedrock_model_id
        ),
    )
    return ReconciliationCaseService(graph, banking, CaseRepository())


app = FastAPI(
    title="Agentic Bank Reconciliation Service",
    version="1.0.0",
    description="Investigates exceptions and pauses before financial state changes.",
)
app.state.case_service = build_service()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "agent-service",
        "llm_provider": settings.llm_provider,
    }


@app.post("/investigate", response_model=CaseRecord)
async def investigate(request: InvestigateRequest) -> CaseRecord:
    try:
        return await app.state.case_service.investigate(request.transaction_id.strip().upper())
    except BankingServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/cases/{case_id}", response_model=CaseRecord)
def get_case(case_id: str) -> CaseRecord:
    try:
        return app.state.case_service.get(case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc


@app.get("/cases/{case_id}/audit", response_model=list[AuditEvent])
def get_audit(case_id: str) -> list[AuditEvent]:
    return get_case(case_id).audit_trail


@app.post("/cases/{case_id}/approve", response_model=CaseRecord)
async def approve_case(case_id: str, request: DecisionRequest) -> CaseRecord:
    try:
        return await app.state.case_service.approve(case_id, request)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
    except InvalidCaseStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BankingServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/cases/{case_id}/reject", response_model=CaseRecord)
def reject_case(case_id: str, request: DecisionRequest) -> CaseRecord:
    try:
        return app.state.case_service.reject(case_id, request)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
    except InvalidCaseStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
