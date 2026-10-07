from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .llm import RecommendationProvider
from .models import Difference, Invoice, PolicyEvidence, Recommendation, ToolTraceEntry, Transaction
from .rag import PolicyRetriever
from .tools import BankingClient, calculate_difference, recommend_resolution


class AgentState(TypedDict, total=False):
    transaction_id: str
    transaction: Transaction
    invoice: Invoice | None
    difference: Difference
    policy_evidence: list[PolicyEvidence]
    recommended_action: Recommendation
    policy_query: str
    base_explanation: str
    tool_trace: list[ToolTraceEntry]


class ReconciliationGraph:
    def __init__(
        self,
        banking: BankingClient,
        retriever: PolicyRetriever,
        provider: RecommendationProvider,
    ) -> None:
        self.banking = banking
        self.retriever = retriever
        self.provider = provider
        builder = StateGraph(AgentState)
        builder.add_node("get_transaction", self._get_transaction)
        builder.add_node("get_invoice", self._get_invoice)
        builder.add_node("calculate_difference", self._calculate_difference)
        builder.add_node("search_policy", self._search_policy)
        builder.add_node("recommend_resolution", self._recommend_resolution)
        builder.add_edge(START, "get_transaction")
        builder.add_edge("get_transaction", "get_invoice")
        builder.add_edge("get_invoice", "calculate_difference")
        builder.add_edge("calculate_difference", "search_policy")
        builder.add_edge("search_policy", "recommend_resolution")
        builder.add_edge("recommend_resolution", END)
        self.graph = builder.compile()

    @staticmethod
    def _append(state: AgentState, entry: ToolTraceEntry) -> list[ToolTraceEntry]:
        return [*state.get("tool_trace", []), entry]

    async def _get_transaction(self, state: AgentState) -> AgentState:
        transaction = await self.banking.get_transaction(state["transaction_id"])
        return {
            "transaction": transaction,
            "tool_trace": self._append(
                state, ToolTraceEntry(tool="get_transaction", summary="Loaded banking transaction")
            ),
        }

    async def _get_invoice(self, state: AgentState) -> AgentState:
        reference = state["transaction"].reference
        invoice = await self.banking.get_invoice(reference) if reference else None
        summary = "Loaded matching invoice" if invoice else "No matching invoice was available"
        return {
            "invoice": invoice,
            "tool_trace": self._append(
                state, ToolTraceEntry(tool="get_invoice", summary=summary, success=invoice is not None)
            ),
        }

    def _calculate_difference(self, state: AgentState) -> AgentState:
        difference = calculate_difference(state["transaction"], state.get("invoice"))
        action, explanation, query = recommend_resolution(
            state["transaction"], state.get("invoice"), difference
        )
        return {
            "difference": difference,
            "policy_query": query,
            "base_explanation": explanation,
            "recommended_action": Recommendation(
                action=action, explanation=explanation, confidence=0, requires_approval=True
            ),
            "tool_trace": self._append(
                state,
                ToolTraceEntry(
                    tool="calculate_difference",
                    summary=f"Computed difference: {difference.amount_difference}",
                ),
            ),
        }

    def _search_policy(self, state: AgentState) -> AgentState:
        evidence = self.retriever.search(state["policy_query"])
        return {
            "policy_evidence": evidence,
            "tool_trace": self._append(
                state,
                ToolTraceEntry(
                    tool="search_policy",
                    summary=f"Retrieved {len(evidence)} relevant policy sections",
                ),
            ),
        }

    def _recommend_resolution(self, state: AgentState) -> AgentState:
        draft = state["recommended_action"]
        recommendation = self.provider.explain(
            state["transaction"],
            state.get("invoice"),
            state["difference"],
            state["policy_evidence"],
            draft.action,
            state["base_explanation"],
        )
        return {
            "recommended_action": recommendation,
            "tool_trace": self._append(
                state,
                ToolTraceEntry(
                    tool="recommend_resolution",
                    summary=f"Recommended {recommendation.action}; execution withheld",
                ),
            ),
        }

    async def investigate(self, transaction_id: str) -> AgentState:
        return await self.graph.ainvoke({"transaction_id": transaction_id, "tool_trace": []})
