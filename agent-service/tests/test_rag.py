from pathlib import Path

from app.rag import PolicyRetriever


POLICY = Path(__file__).resolve().parents[2] / "policies" / "reconciliation_policy.md"


def test_retrieves_minor_discrepancy_policy() -> None:
    results = PolicyRetriever(POLICY).search("difference 20 EUR minor discrepancy")
    assert results[0].section == "Minor payment discrepancy"
    assert "25 EUR" in results[0].text


def test_retrieves_human_approval_control() -> None:
    results = PolicyRetriever(POLICY).search("state changing action human approval")
    assert any(item.section == "Human approval control" for item in results)
