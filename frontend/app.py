import os
from typing import Any

import httpx
import streamlit as st


AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8000").rstrip("/")
DEMO_TRANSACTIONS = ["TX1001", "TX1002", "TX1003", "TX1004", "TX1005", "TX1006"]

st.set_page_config(
    page_title="Agentic Bank Reconciliation",
    page_icon="🏦",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 1200px; padding-top: 2rem;}
      [data-testid="stMetric"] {background: #f5f7fb; border: 1px solid #e2e8f0; padding: 1rem; border-radius: .6rem;}
      .safety {background: #fff8e6; border-left: 4px solid #eab308; padding: .8rem 1rem; border-radius: .3rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = httpx.request(method, f"{AGENT_SERVICE_URL}{path}", timeout=20, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        raise RuntimeError(detail) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Agent service is unavailable: {exc}") from exc


def load_case(case_id: str) -> None:
    st.session_state.case = api("GET", f"/cases/{case_id}")


st.title("Agentic Bank Reconciliation")
st.caption("Explainable exception investigation with policy evidence and human approval")
st.markdown(
    '<div class="safety"><strong>Safety control:</strong> The agent investigates and recommends only. '
    "No banking record changes until a human explicitly approves.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Investigation")
    choice = st.selectbox("Demo transaction", [*DEMO_TRANSACTIONS, "Custom ID"])
    transaction_id = (
        st.text_input("Transaction ID", placeholder="TX1003") if choice == "Custom ID" else choice
    )
    if st.button("Investigate", type="primary", use_container_width=True):
        if not transaction_id.strip():
            st.warning("Enter a transaction ID.")
        else:
            try:
                with st.spinner("Agent is investigating..."):
                    st.session_state.case = api(
                        "POST", "/investigate", json={"transaction_id": transaction_id}
                    )
            except RuntimeError as exc:
                st.error(str(exc))
    st.divider()
    st.caption(f"Agent API: {AGENT_SERVICE_URL}")
    st.caption("All displayed banking data is synthetic.")

case = st.session_state.get("case")
if not case:
    st.info("Select a transaction and click **Investigate**. Try TX1003 for a minor discrepancy.")
    st.subheader("Demo scenarios")
    st.table(
        {
            "Transaction": DEMO_TRANSACTIONS,
            "Scenario": [
                "Exact match",
                "Exact match",
                "€20 minor discrepancy",
                "Missing invoice reference",
                "Currency mismatch",
                "Unknown invoice",
            ],
        }
    )
    st.stop()

status = case["final_status"]
status_icon = {"WAITING_FOR_APPROVAL": "⏳", "RESOLVED": "✅", "REJECTED": "⛔"}.get(status, "⚠️")
st.subheader(f"Case {case['case_id'][:8]} · {status_icon} {status.replace('_', ' ').title()}")

transaction = case["transaction"]
invoice = case.get("invoice")
difference = case["difference"]
cols = st.columns(4)
cols[0].metric("Received", f"{transaction['amount']:,.2f} {transaction['currency']}")
expected = difference.get("expected_amount")
cols[1].metric("Expected", f"{expected:,.2f} {invoice['currency']}" if expected is not None else "Unavailable")
delta = difference.get("amount_difference")
cols[2].metric("Difference", f"{delta:,.2f} {transaction['currency']}" if delta is not None else "N/A")
cols[3].metric("Confidence", f"{case['recommended_action']['confidence']:.0%}")

left, right = st.columns(2)
with left:
    st.markdown("#### Banking transaction")
    st.json(transaction)
with right:
    st.markdown("#### Accounting invoice")
    if invoice:
        st.json(invoice)
    else:
        st.warning("No matching invoice found.")

st.markdown("#### Agent execution trace")
st.dataframe(
    [
        {"Step": index + 1, "Tool": item["tool"], "Result": item["summary"], "Success": item["success"]}
        for index, item in enumerate(case["tool_trace"])
    ],
    hide_index=True,
    use_container_width=True,
)

recommendation = case["recommended_action"]
st.markdown("#### Recommendation")
st.success(f"**{recommendation['action'].replace('_', ' ').title()}** — {recommendation['explanation']}")

st.markdown("#### Policy evidence")
for evidence in case["policy_evidence"]:
    with st.expander(f"{evidence['section']} · relevance {evidence['score']:.0%}"):
        st.write(evidence["text"])

if status == "WAITING_FOR_APPROVAL":
    st.markdown("#### Human decision")
    reason = st.text_input("Decision note (optional)", max_chars=500)
    approve_col, reject_col, _ = st.columns([1, 1, 3])
    if approve_col.button("Approve action", type="primary", use_container_width=True):
        try:
            st.session_state.case = api(
                "POST",
                f"/cases/{case['case_id']}/approve",
                json={"decided_by": "streamlit-reviewer", "reason": reason or None},
            )
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    if reject_col.button("Reject", use_container_width=True):
        try:
            st.session_state.case = api(
                "POST",
                f"/cases/{case['case_id']}/reject",
                json={"decided_by": "streamlit-reviewer", "reason": reason or None},
            )
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

st.markdown("#### Audit trail")
st.dataframe(
    [
        {"Timestamp": event["timestamp"], "Event": event["event"], "Details": str(event["details"])}
        for event in case["audit_trail"]
    ],
    hide_index=True,
    use_container_width=True,
)
