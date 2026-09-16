CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL DEFAULT 'borrower',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS item_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        daily_late_fee REAL NOT NULL DEFAULT 0,
        deposit_amount REAL NOT NULL DEFAULT 0,
        default_loan_days INTEGER NOT NULL DEFAULT 3,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_type_id INTEGER NOT NULL,
        asset_tag TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'available',
        condition_note TEXT,
        current_loan_id INTEGER,
        FOREIGN KEY (item_type_id) REFERENCES item_types(id),
        FOREIGN KEY (current_loan_id) REFERENCES loans(id),
        UNIQUE (current_loan_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrower_id INTEGER NOT NULL,
        stock_unit_id INTEGER NOT NULL,
        borrowed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        due_at TEXT NOT NULL,
        returned_at TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        deposit_amount REAL NOT NULL DEFAULT 0,
        late_fee_amount REAL NOT NULL DEFAULT 0,
        refund_amount REAL NOT NULL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (borrower_id) REFERENCES users(id),
        FOREIGN KEY (stock_unit_id) REFERENCES stock_units(id),
        CHECK (status IN ('active', 'returned', 'overdue', 'cancelled')),
        CHECK (late_fee_amount >= 0),
        CHECK (refund_amount >= 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS loan_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        from_borrower_id INTEGER NOT NULL,
        to_borrower_id INTEGER NOT NULL,
        transferred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (loan_id) REFERENCES loans(id),
        FOREIGN KEY (from_borrower_id) REFERENCES users(id),
        FOREIGN KEY (to_borrower_id) REFERENCES users(id)
    )
    """,
]

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_stock_units_item_type ON stock_units(item_type_id)",
    "CREATE INDEX IF NOT EXISTS idx_stock_units_status ON stock_units(status)",
    "CREATE INDEX IF NOT EXISTS idx_loans_borrower ON loans(borrower_id)",
    "CREATE INDEX IF NOT EXISTS idx_loans_stock_unit ON loans(stock_unit_id)",
    "CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status)",
    "CREATE INDEX IF NOT EXISTS idx_loans_due_at ON loans(due_at)",
    "CREATE INDEX IF NOT EXISTS idx_loan_transfers_loan ON loan_transfers(loan_id)",
]
