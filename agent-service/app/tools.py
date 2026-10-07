import httpx

from .models import Difference, Invoice, Transaction


class BankingServiceError(RuntimeError):
    pass


class BankingClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, transport=self.transport, timeout=10
            ) as client:
                response = await client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise BankingServiceError(f"Banking service unavailable: {exc}") from exc
        return response

    async def get_transaction(self, transaction_id: str) -> Transaction:
        response = await self._request("GET", f"/transactions/{transaction_id}")
        if response.status_code == 404:
            raise BankingServiceError(f"Transaction {transaction_id} was not found")
        if response.is_error:
            raise BankingServiceError(
                f"Banking service error ({response.status_code}): {response.text}"
            )
        return Transaction.model_validate(response.json())

    async def get_invoice(self, invoice_reference: str) -> Invoice | None:
        response = await self._request("GET", f"/invoices/{invoice_reference}")
        if response.status_code == 404:
            return None
        if response.is_error:
            raise BankingServiceError(
                f"Banking service error ({response.status_code}): {response.text}"
            )
        return Invoice.model_validate(response.json())

    async def resolve_transaction(self, transaction_id: str, case_id: str, action: str) -> dict:
        response = await self._request(
            "POST",
            f"/transactions/{transaction_id}/resolve",
            json={"case_id": case_id, "action": action, "approval_status": "APPROVED"},
        )
        if response.is_error:
            raise BankingServiceError(
                f"Resolution failed ({response.status_code}): {response.text}"
            )
        return response.json()


def calculate_difference(transaction: Transaction, invoice: Invoice | None) -> Difference:
    if invoice is None:
        return Difference(
            expected_amount=None,
            received_amount=transaction.amount,
            amount_difference=None,
            currency_match=None,
        )
    return Difference(
        expected_amount=invoice.expected_amount,
        received_amount=transaction.amount,
        amount_difference=round(invoice.expected_amount - transaction.amount, 2),
        currency_match=invoice.currency == transaction.currency,
    )


def recommend_resolution(
    transaction: Transaction, invoice: Invoice | None, difference: Difference
) -> tuple[str, str, str]:
    if not transaction.reference:
        return (
            "MANUAL_REFERENCE_REVIEW",
            "The payment has no invoice reference, so it cannot be matched safely.",
            "missing payment reference manual investigation human approval",
        )
    if invoice is None:
        return (
            "INVESTIGATE_UNKNOWN_INVOICE",
            f"No accounting invoice exists for reference {transaction.reference}.",
            "unknown invoice manual investigation human approval",
        )
    if difference.currency_match is False:
        return (
            "INVESTIGATE_CURRENCY_MISMATCH",
            f"The payment currency {transaction.currency} differs from invoice currency {invoice.currency}.",
            "currency mismatch FX currency investigation human approval",
        )
    if difference.amount_difference == 0:
        return (
            "MARK_RECONCILED",
            "Reference, amount, and currency match the accounting invoice.",
            "exact amount reference match reconciled human approval",
        )
    if difference.amount_difference is not None and abs(difference.amount_difference) <= 25:
        return (
            "ACCEPT_MINOR_DISCREPANCY",
            f"The received amount differs from the invoice by {abs(difference.amount_difference):.2f} {transaction.currency}, within the minor-discrepancy threshold.",
            "difference 25 EUR minor payment discrepancy human approval",
        )
    return (
        "MANUAL_REFERENCE_REVIEW",
        "The amount discrepancy exceeds the permitted minor threshold.",
        "amount difference exceeds threshold manual investigation human approval",
    )
