# Reconciliation Policy

## Exact match

- When invoice reference, amount, and currency match, recommend marking the transaction reconciled.
- Even an exact match requires human approval before the banking record is changed.

## Minor payment discrepancy

- An absolute amount difference of 25 EUR or less is a minor payment discrepancy.
- Recommend accepting the minor discrepancy, subject to explicit human approval.

## Missing payment reference

- A payment without an invoice reference cannot be automatically matched.
- Route the case to manual reference investigation.

## Currency mismatch

- When payment and invoice currencies differ, route the case to FX/currency investigation.
- Do not infer an exchange rate or alter an amount automatically.

## Unknown invoice

- When the referenced invoice is not found, route the case to manual invoice investigation.
- Do not create an invoice automatically.

## Human approval control

- Every state-changing financial action requires explicit human approval.
- Investigation and recommendation are read-only. Rejection must not change the banking transaction.
