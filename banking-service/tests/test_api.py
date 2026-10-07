from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_list_transactions() -> None:
    assert client.get("/health").json()["status"] == "healthy"
    assert len(client.get("/transactions").json()) == 6


def test_minor_discrepancy_data_is_available() -> None:
    transaction = client.get("/transactions/TX1003").json()
    invoice = client.get("/invoices/INV-1003").json()
    assert transaction["amount"] == 980.0
    assert invoice["expected_amount"] == 1000.0


def test_resolution_requires_human_approval() -> None:
    response = client.post(
        "/transactions/TX1003/resolve",
        json={"case_id": "case-1", "action": "ACCEPT_MINOR_DISCREPANCY", "approval_status": "PENDING"},
    )
    assert response.status_code == 403


def test_approved_resolution_is_executed() -> None:
    response = client.post(
        "/transactions/TX1002/resolve",
        json={"case_id": "case-2", "action": "MARK_RECONCILED", "approval_status": "APPROVED"},
    )
    assert response.status_code == 200
    assert response.json()["transaction"]["status"] == "RESOLVED"
