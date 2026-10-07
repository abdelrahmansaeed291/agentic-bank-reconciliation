import re
from pathlib import Path

from .models import PolicyEvidence


class PolicyRetriever:
    """Explainable local retrieval based on token overlap; no model or network required."""

    def __init__(self, policy_path: Path) -> None:
        if not policy_path.exists():
            raise FileNotFoundError(f"Policy document not found: {policy_path}")
        self.sections = self._parse(policy_path.read_text(encoding="utf-8"))

    @staticmethod
    def _parse(document: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        heading = "Policy"
        body: list[str] = []
        for line in document.splitlines():
            if line.startswith("## "):
                if body:
                    sections.append((heading, " ".join(body).strip()))
                heading, body = line[3:].strip(), []
            elif line.strip() and not line.startswith("# "):
                body.append(line.strip().lstrip("- "))
        if body:
            sections.append((heading, " ".join(body).strip()))
        return sections

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    def search(self, query: str, limit: int = 2) -> list[PolicyEvidence]:
        query_tokens = self._tokens(query)
        ranked: list[PolicyEvidence] = []
        for heading, text in self.sections:
            tokens = self._tokens(f"{heading} {text}")
            overlap = len(query_tokens & tokens)
            score = overlap / max(len(query_tokens), 1)
            ranked.append(PolicyEvidence(section=heading, text=text, score=round(score, 3)))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]
