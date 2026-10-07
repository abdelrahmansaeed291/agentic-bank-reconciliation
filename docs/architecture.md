# Architecture

## Design goals

The project optimizes for interview clarity: every boundary is visible, demo mode is offline and deterministic, and financial writes are isolated behind explicit approval. It is deliberately a small three-service system rather than an enterprise platform.

```mermaid
flowchart LR
    User --> UI[Streamlit frontend]
    UI --> API[FastAPI agent service]
    API --> Graph[LangGraph workflow]
    Graph --> Tools[Read-only tools]
    Tools --> Bank[Mock banking service]
    Graph --> Policy[Local policy retrieval]
    Graph --> Wait[WAITING_FOR_APPROVAL]
    Wait -->|Approve| Write[resolve_transaction]
    Wait -->|Reject| Rejected[REJECTED]
    Write --> Resolved[RESOLVED]
    API --> Audit[(In-memory case and audit store)]
```

## Responsibilities

- **Banking service:** owns synthetic transactions/invoices and the guarded state-changing endpoint.
- **Agent service:** coordinates tools, policy retrieval, recommendations, approval state, and audit history.
- **Frontend:** presents evidence and collects the human decision; it contains no reconciliation rules.
- **Policy retriever:** parses Markdown sections and ranks them by transparent token overlap. This keeps offline demo behavior fast and explainable. An embedding retriever can replace it behind the same boundary later.
- **Recommendation provider:** deterministic demo provider by default; optional Amazon Bedrock provider for natural-language explanations.

## LangGraph flow

```mermaid
flowchart TD
    A[get_transaction] --> B[get_invoice]
    B --> C[calculate_difference]
    C --> D[search_policy]
    D --> E[recommend_resolution]
    E --> F[WAITING_FOR_APPROVAL]
```

Each node adds an entry to `tool_trace`. The graph ends after recommendation. Approval is a separate API command, which makes the safety boundary straightforward to test and explain.

## Trust boundaries and limitations

This demonstration has no authentication and uses in-memory state, so it is not production-ready. In a real bank, identity/RBAC, a durable database, idempotency controls, signed approval claims, encryption, observability, and segregation-of-duties controls would be required. No real customer data is used here.
