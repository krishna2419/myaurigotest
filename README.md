# AV Gear Hub - Equipment Lending Management

AV Gear Hub is a Flask and SQLite application for managing physical AV equipment lending. It replaces paper-based registers with current availability, physical stock-unit tracking, borrowing limits, due dates, returns, late fees, refundable deposits, overdue reminders, and active-loan transfers.

## Problem Statement

Paper-based AV equipment lending records become outdated quickly. Staff need a reliable answer to availability questions, including which copy of an item is available. Borrowers can return equipment late, deposits and fees need consistent handling, and borrowing limits prevent one person from taking too much equipment. The system also supports transferring an active loan to another borrower without changing the physical equipment assignment or original due date.

## Key Features

- Equipment inventory and physical stock-unit tracking
- Unique asset tags for physical units
- Real-time availability checks
- Quantity-based borrowing
- Maximum active-loan limit
- Equipment-specific due dates
- Active-loan and overdue tracking
- Daily late-fee calculation
- Refundable deposits and refund calculation
- Good, Damaged, and Lost return conditions
- Due-soon and due-today in-app reminders
- Active-loan transfer between borrowers
- Transfer history in `loan_transfers`
- Dashboard summaries and responsive AV Gear Hub UI
- SQLite persistence with seeded demo data

## Tech Stack

- Python 3
- Flask 3.0.3
- SQLite via Python's built-in `sqlite3` module
- Jinja2 templates through Flask
- HTML and CSS
- Lightweight vanilla JavaScript for responsive navigation and client-side table filtering
- No frontend framework, CDN, or additional runtime dependency

## Project Structure

```text
.
├── run.py                         # Flask development entry point
├── requirements.txt               # Flask dependency
├── README.md
├── REASONING.md
├── data/
│   └── app.db                     # Local SQLite database
└── app/
    ├── __init__.py                # Application factory and blueprint registration
    ├── config.py                  # Database path and MAX_ACTIVE_LOANS
    ├── db.py                      # Connections, seed data, queries, transactions
    ├── models.py                  # SQLite table and index definitions
    ├── routes/
    │   ├── dashboard.py           # Dashboard, equipment, loans, overdue routes
    │   ├── borrow.py              # Borrowing workflow
    │   ├── returns.py             # Return workflow
    │   ├── transfers.py            # Active-loan transfer workflow
    │   ├── home.py                # Legacy unregistered foundation route
    │   └── __init__.py
    ├── templates/                 # Jinja2 pages and shared base layout
    └── static/
        ├── css/style.css          # Shared AV Gear Hub design system
        └── js/app.js              # Mobile navigation and table filtering
```

The current application factory registers the dashboard, borrowing, return, and transfer blueprints. `home.py` and `index.html` remain as legacy foundation files but are not registered; `/` is provided by the dashboard blueprint.

## Data Model

### Users

Borrowers and staff users. Borrowing and transfer targets must use valid borrower accounts.

### Item Types

Equipment definitions such as DSLR Camera, Projector, Lavalier Mic, and Tripod. Each type stores its category, daily late fee, deposit amount, default loan duration, and active flag.

### Stock Units

Individual physical equipment units with unique asset tags, status, condition notes, and an optional current loan relationship.

### Loans

A borrowing record for one physical stock unit.

**One loan represents one physical stock unit.** Borrowing multiple copies creates multiple loan records, each connected to a different stock unit.

### Loan Transfers

`loan_transfers` records successful ownership changes with the original loan ID, previous borrower, new borrower, and transfer timestamp. The loan remains the source of truth for the current borrower and active state.

## Business Rules

### Availability

A physical unit is borrowable only when:

- `status = 'available'`
- `current_loan_id IS NULL`

Damaged and lost units are not available. Dashboard and inventory availability counts apply both conditions.

### Borrowing Limit

The configured maximum is:

```python
MAX_ACTIVE_LOANS = 3
```

The limit counts loans where `returned_at IS NULL`. The borrowing form displays current usage and remaining capacity. Transfer validation applies the same limit to the target borrower.

### Due Dates

When a loan is created, its due date is the borrowing timestamp plus the selected equipment type's `default_loan_days` value.

### Late Fees

```text
late fee = days overdue × daily late fee
```

Overdue pages show an estimated fee. The stored loan `late_fee_amount` is updated only when the equipment is returned.

### Deposit Refunds

```text
refund = max(0, deposit - late fee)
```

The original deposit, final late fee, and refund are stored on the loan.

### Return Conditions

- Good: the stock unit becomes `available`
- Damaged: the stock unit becomes `damaged`
- Lost: the stock unit becomes `lost`

Every return clears `current_loan_id`; damaged and lost equipment remains unavailable.

### Loan Transfers

Only an active or overdue, unreturned loan can be transferred. The target borrower must exist, be different from the current borrower, and have capacity below the active-loan limit.

A successful transfer:

- updates the existing loan row in place
- changes only the borrower ownership
- preserves the loan ID
- preserves `stock_unit_id`
- preserves `borrowed_at`
- preserves `due_at` exactly
- leaves stock status and availability unchanged
- records a row in `loan_transfers`

The transferred loan continues to belong to the new borrower. If it is later returned late, the original due date is still used for fee calculation.

## How to Use the Application

1. Open the dashboard to see total, available, borrowed, overdue, damaged, and lost units.
2. Open Equipment to review category cards and individual physical stock units.
3. Open Borrow Equipment, select a borrower, equipment type, and quantity, then confirm the loan.
4. Monitor Active Loans for status, due dates, deposits, Return actions, and Transfer actions.
5. Return equipment by selecting its condition. The system updates inventory and calculates the fee/refund result.
6. Transfer an active loan by selecting Transfer, choosing another borrower, and confirming. The original due date and physical unit remain unchanged.
7. Open Overdue to review active late loans, days overdue, daily fees, and estimated fees.

## Main Routes

| Route | Purpose |
| --- | --- |
| `/` | Dashboard summary, recent activity, reminders, and overdue overview |
| `/equipment` | Equipment type cards, availability, and physical stock units |
| `/loans` | Active loans with Return and Transfer actions |
| `/borrow` | Borrowing form and borrower capacity visibility |
| `/overdue` | Active overdue loans and estimated late fees |
| `/return/<loan_id>` | Return form and return confirmation |
| `/transfer/<loan_id>` | Active-loan transfer form and confirmation |

The borrowing, return, and transfer workflows support `GET` and `POST` requests as implemented by their routes.

## Setup

From a fresh checkout:

```bash
git clone <repository-url>
cd myaurigotest
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

The application creates its SQLite tables and inserts demo data automatically when `create_app()` starts. To explicitly reset and reseed the local database:

```bash
python3 - <<'PY'
from app.db import reset_database, seed_demo_data

reset_database()
seed_demo_data()
PY
```

## Running the Application

```bash
python3 run.py
```

`run.py` starts Flask with `debug=True`, binds to `0.0.0.0`, and uses port `5000`. Open:

```text
http://127.0.0.1:5000/
```

If port `5000` is already occupied, stop the existing Flask process before starting another instance.

## Testing and Verification

There is no committed pytest or unittest suite. Development verification used Flask's test client and direct SQLite assertions. The checks covered:

- separate physical units and unique asset tags
- accurate availability and borrowed counts
- single- and multi-unit borrowing
- double-booking protection and transaction-time availability checks
- invalid borrowers, equipment, quantities, and capacity limits
- due dates and deposits
- Good, Damaged, and Lost returns
- late days, late fees, and non-negative refunds
- overdue tracking and due-soon/due-today reminders
- active-loan transfers and transfer-history records
- unchanged loan identity, stock unit, due date, and availability after transfer
- transfer limit rejection, invalid cases, and double-return protection
- transaction rollback and database consistency
- route regression and template rendering
- responsive UI route smoke checks

The available static check is:

```bash
python3 -m compileall -q app run.py
git diff --check
```

## Debugging and Troubleshooting

### Reset demo data

Run the reset/reseed snippet in the Setup section. The local database is stored at `data/app.db`.

### Inspect database counts

```bash
python3 - <<'PY'
from app.db import get_connection

connection = get_connection()
for table in ("users", "item_types", "stock_units", "loans", "loan_transfers"):
    count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(table, count)
connection.close()
PY
```

### Check Python errors

```bash
python3 -m compileall -q app run.py
```

### Check a stale browser or Flask process

If templates appear outdated, inspect the process listening on port `5000`, stop the stale Flask process, and start the current checkout again:

```bash
lsof -nP -iTCP:5000 -sTCP:LISTEN
python3 run.py
```

A browser hard refresh (`Ctrl+Shift+R`) may also be needed after frontend changes.

## Future Improvements

These are future ideas, not implemented functionality:

- Authentication and role-based access control
- Reservations
- Email or scheduled external notifications
- Payment processing
- Detailed audit history beyond transfers
- Richer reporting and analytics
- Production deployment and a database such as PostgreSQL
