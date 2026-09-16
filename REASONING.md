# Reasoning

## Problem Interpretation

The prompt describes a lending desk that has outgrown paper records. The important operational problems are unreliable availability, multiple physical copies, conflicting borrowing requests, delayed returns, late fees, deposits, excessive borrowing, and the need to transfer an active loan to another borrower without moving the physical asset.

The solution prioritizes accurate physical-unit state, simple staff workflows, explainable business rules, and a small amount of operational visibility for upcoming and overdue returns.

## Requirements Identified

The system must provide:

- inventory visibility at both equipment-type and physical-unit level
- safe quantity-based borrowing
- one loan per physical stock unit
- due dates and refundable deposits
- late-fee and refund calculations
- Good, Damaged, and Lost returns
- active-loan limits
- overdue and due-soon indicators
- transfer of an active loan between valid borrowers
- preservation of the original loan and physical-unit identity during transfer
- a lightweight, usable interface for a lending desk

## Solution Approach

The implementation uses server-rendered Flask routes, SQLite queries, and Jinja2 templates. This keeps persistence and request handling close to the code that uses them, which is appropriate for a focused assessment build. It avoids unnecessary services, frontend infrastructure, and dependencies while keeping the workflow easy to run and inspect locally.

## Architecture Choice

Flask provides the application factory, route registration, request handling, and template rendering. SQLite provides a local relational database with transactions and foreign keys. Database access is centralized in `app/db.py`; schema and indexes are defined in `app/models.py`; route modules coordinate database operations and templates; shared presentation lives in the base template and static assets.

This is a deliberately lightweight architecture. It has not been presented as a tested production-scale deployment.

## Data Model

The core tables are `users`, `item_types`, `stock_units`, `loans`, and `loan_transfers`.

- `users` identifies borrowers and staff.
- `item_types` stores equipment-level rules such as deposit, daily fee, and loan duration.
- `stock_units` represents individual physical assets and their current status.
- `loans` records borrowing and return state.
- `loan_transfers` records successful changes in loan ownership.

## Physical Stock-Unit Design

An Item Type such as Projector describes a category of equipment. A Stock Unit such as `PRO-01` describes one physical projector. Separating these concepts allows multiple copies to be tracked independently by asset tag, status, condition, borrower, and due date.

## Availability Logic

A unit is available only when its status is `available` and its `current_loan_id` is `NULL`. Borrowing queries apply both conditions, and dashboard/inventory counts use the same definition. This prevents a damaged, lost, or inconsistently linked unit from being offered as available.

## Borrowing Logic

A borrowing request validates the borrower, active equipment type, positive integer quantity, stock availability, and active-loan capacity. The system selects individual available stock units and creates one loan row per selected unit. The stock units are then linked to those loans and marked borrowed.

## Return and Late-Fee Logic

A return validates that the loan is active and that its stock unit still points to it. The return timestamp is compared to the stored `due_at`. Late days are calculated from that original due date, and the late fee is:

```text
days overdue × daily late fee
```

The loan and stock unit are updated together. Good returns become available; Damaged and Lost returns remain unavailable.

## Deposit and Refund Logic

The deposit amount is stored on each loan at borrowing time. At return, the refund is calculated as:

```text
max(0, deposit - late fee)
```

Keeping the deposit, late fee, and refund on the loan preserves the financial outcome of the completed transaction.

## Borrowing Limit

`MAX_ACTIVE_LOANS` is configured as `3`. The application counts loans with `returned_at IS NULL`. The limit is displayed in the borrowing UI and enforced again inside the borrowing transaction. A returned loan therefore frees capacity.

## Overdue and Reminder Logic

Overdue state is derived from the current time, `due_at`, and the absence of `returned_at`; it does not rely only on a stored status that could become stale. The `/overdue` view shows days overdue, daily late fee, and an estimated fee. The dashboard identifies active loans due within the next two days and distinguishes loans due today.

These reminders are intentionally in-app. Email, SMS, push, scheduling, and external notification infrastructure are outside the current scope.

## Loan Transfer Design

An active or overdue unreturned loan is transferred by updating the existing loan row in place. Only `borrower_id` changes.

The transfer preserves:

- the original loan ID
- `stock_unit_id`
- `borrowed_at`
- `due_at`
- the stock unit's status
- equipment availability

No new loan is created, and the item is not returned and borrowed again. The transferred loan belongs to the new borrower for future active-loan counting and return handling. Because `due_at` remains unchanged, a later late return still calculates fees from the original due date.

Successful transfers are recorded separately in `loan_transfers` with the loan ID, previous borrower, new borrower, and timestamp. The target borrower's active-loan limit is checked inside the same transaction.

## Transaction Safety

Borrowing and returning use `BEGIN IMMEDIATE` and commit related changes together. Transfer uses the same transaction boundary: it validates the active loan, target borrower, borrower difference, and target capacity, then updates the loan and inserts the history row before committing. Any validation or database failure rolls the transaction back.

This preserves the important invariants that a stock unit is not temporarily made available during transfer, a multi-unit borrow does not partially commit, and a return cannot leave a returned loan occupying its stock unit.

## UI/UX Decisions

The interface uses a shared Jinja base template and a custom CSS system rather than a frontend framework. The AV Gear Hub visual language uses a dark navigation rail, teal action color, neutral surfaces, clear status badges, compact tables, equipment cards, availability meters, responsive layouts, and concise feedback states.

The dashboard is the operational entry point. Equipment cards make category-level availability scannable while physical-unit tables preserve detail. Active-loan rows expose Return and Transfer actions directly. Return conditions use visually distinct choices, and transfer pages show which values stay unchanged. Lightweight vanilla JavaScript provides mobile sidebar behavior and client-side table filtering without changing backend behavior.

## Testing Strategy

Verification combined Flask test-client requests with direct SQLite assertions and controlled due dates. The testing covered inventory counts, unique physical units, multi-unit borrowing, invalid input, borrowing limits, due dates, deposits, all return conditions, late fees, refunds, overdue/reminder behavior, transfer invariants, transfer history, transfer-limit rejection, invalid transfers, returned-loan rejection, rollback, route regressions, template rendering, and database consistency.

The final checks also compiled the Python application, checked diff whitespace, smoke-tested the primary routes, exercised borrow/transfer/return POST workflows, and reset the database to seeded demo data.

## Trade-offs and Future Improvements

The project intentionally omits authentication, reservations, payment processing, external notifications, React, microservices, and external infrastructure. Those additions would increase scope without being required to prove the core lending workflow.

Future improvements could include authentication and authorization, reservations, scheduled notifications, richer audit history, reporting, production deployment, and migration to a production database such as PostgreSQL.
