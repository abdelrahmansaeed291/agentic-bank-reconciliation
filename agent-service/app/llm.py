from abc import ABC, abstractmethod
import json

from .models import Difference, Invoice, PolicyEvidence, Recommendation, Transaction


class RecommendationProvider(ABC):
    @abstractmethod
    def explain(
        self,
        transaction: Transaction,
        invoice: Invoice | None,
        difference: Difference,
        evidence: list[PolicyEvidence],
        action: str,
        base_explanation: str,
    ) -> Recommendation:
        """Create an evidence-grounded recommendation without executing it."""


class DemoRecommendationProvider(RecommendationProvider):
    def explain(
        self,
        transaction: Transaction,
        invoice: Invoice | None,
        difference: Difference,
        evidence: list[PolicyEvidence],
        action: str,
        base_explanation: str,
    ) -> Recommendation:
        confidence = 0.98 if invoice and difference.amount_difference == 0 else 0.9
        if invoice is None or difference.currency_match is False:
            confidence = 0.85
        policy_sections = ", ".join(item.section for item in evidence)
        explanation = f"{base_explanation} Policy evidence: {policy_sections}."
        return Recommendation(
            action=action,
            explanation=explanation,
            confidence=confidence,
            requires_approval=True,
        )


class BedrockRecommendationProvider(RecommendationProvider):
    """Optional provider. boto3 and AWS credentials are only needed in Bedrock mode."""

    def __init__(self, region: str, model_id: str) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3 to use LLM_PROVIDER=bedrock") from exc
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def explain(
        self,
        transaction: Transaction,
        invoice: Invoice | None,
        difference: Difference,
        evidence: list[PolicyEvidence],
        action: str,
        base_explanation: str,
    ) -> Recommendation:
        context = {
            "transaction": transaction.model_dump(),
            "invoice": invoice.model_dump() if invoice else None,
            "difference": difference.model_dump(),
            "policy": [item.model_dump() for item in evidence],
            "recommended_action": action,
        }
        prompt = (
            "Explain this reconciliation recommendation in 2 concise sentences. "
            "Do not propose or claim to execute any action. Use only the supplied facts.\n"
            + json.dumps(context)
        )
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 250, "temperature": 0},
        )
        explanation = response["output"]["message"]["content"][0]["text"]
        return Recommendation(
            action=action,
            explanation=explanation or base_explanation,
            confidence=0.85,
            requires_approval=True,
        )


def create_provider(name: str, region: str, model_id: str) -> RecommendationProvider:
    if name == "demo":
        return DemoRecommendationProvider()
    if name == "bedrock":
        return BedrockRecommendationProvider(region, model_id)
    raise ValueError(f"Unsupported LLM_PROVIDER: {name}")
