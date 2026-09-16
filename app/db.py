import os
import sqlite3
from datetime import datetime, timedelta

from .config import Config
from .models import CREATE_INDEXES, CREATE_TABLES


def get_connection():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    connection = sqlite3.connect(Config.DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()
    try:
        for statement in CREATE_TABLES:
            connection.execute(statement)
        for statement in CREATE_INDEXES:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def table_has_rows(table_name):
    connection = get_connection()
    try:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
        return row["count"] > 0
    finally:
        connection.close()


def reset_database():
    if os.path.exists(Config.DATABASE_PATH):
        os.remove(Config.DATABASE_PATH)
    initialize_database()


def seed_demo_data():
    connection = get_connection()
    try:
        if table_has_rows("users"):
            return

        users = [
            ("Alice Student", "alice@student.example", "borrower"),
            ("Ben Club Rep", "ben@club.example", "borrower"),
            ("Charlie Society Member", "charlie@society.example", "borrower"),
            ("Staff Desk", "staff@desk.example", "staff"),
        ]

        connection.executemany(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            users,
        )

        item_types = [
            ("DSLR Camera", "camera", 8.0, 50.0, 3),
            ("Projector", "projection", 12.0, 80.0, 2),
            ("Lavalier Mic", "audio", 5.0, 20.0, 2),
            ("Tripod", "support", 3.0, 15.0, 3),
        ]

        connection.executemany(
            "INSERT INTO item_types (name, category, daily_late_fee, deposit_amount, default_loan_days) VALUES (?, ?, ?, ?, ?)",
            item_types,
        )

        item_lookup = {
            row["name"]: row["id"]
            for row in connection.execute("SELECT id, name FROM item_types").fetchall()
        }

        stock_units = []
        for item_name, unit_count in {
            "DSLR Camera": 2,
            "Projector": 3,
            "Lavalier Mic": 4,
            "Tripod": 5,
        }.items():
            item_id = item_lookup[item_name]
            prefix = {
                "DSLR Camera": "DSLR",
                "Projector": "PRO",
                "Lavalier Mic": "LAV",
                "Tripod": "TRI",
            }[item_name]
            for index in range(1, unit_count + 1):
                asset_tag = f"{prefix}-{index:02d}"
                status = "available"
                condition_note = None
                if item_name == "DSLR Camera" and index == 1:
                    status = "borrowed"
                elif item_name == "Projector" and index == 1:
                    status = "borrowed"
                elif item_name == "Tripod" and index == 1:
                    status = "damaged"
                    condition_note = "Cracked quick-release plate"
                stock_units.append((item_id, asset_tag, status, condition_note, None))

        connection.executemany(
            "INSERT INTO stock_units (item_type_id, asset_tag, status, condition_note, current_loan_id) VALUES (?, ?, ?, ?, ?)",
            stock_units,
        )

        stock_lookup = {
            row["asset_tag"]: row["id"]
            for row in connection.execute("SELECT id, asset_tag FROM stock_units").fetchall()
        }

        borrower_ids = {row["email"]: row["id"] for row in connection.execute("SELECT id, email FROM users").fetchall()}

        now = datetime.now()

        overdue_loan = (
            borrower_ids["alice@student.example"],
            stock_lookup["DSLR-01"],
            (now - timedelta(days=12)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            None,
            "overdue",
            50.0,
            16.0,
            0.0,
            "Needs return"
        )

        active_loan = (
            borrower_ids["ben@club.example"],
            stock_lookup["PRO-01"],
            (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            (now + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            None,
            "active",
            80.0,
            0.0,
            0.0,
            "Weekend event"
        )

        returned_loan = (
            borrower_ids["charlie@society.example"],
            stock_lookup["TRI-01"],
            (now - timedelta(days=12)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "returned",
            15.0,
            9.0,
            6.0,
            "Returned late"
        )

        connection.execute(
            "INSERT INTO loans (borrower_id, stock_unit_id, borrowed_at, due_at, returned_at, status, deposit_amount, late_fee_amount, refund_amount, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            overdue_loan,
        )
        connection.execute(
            "INSERT INTO loans (borrower_id, stock_unit_id, borrowed_at, due_at, returned_at, status, deposit_amount, late_fee_amount, refund_amount, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            active_loan,
        )
        connection.execute(
            "INSERT INTO loans (borrower_id, stock_unit_id, borrowed_at, due_at, returned_at, status, deposit_amount, late_fee_amount, refund_amount, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            returned_loan,
        )

        for asset_tag in ["DSLR-01", "PRO-01"]:
            unit_id = stock_lookup[asset_tag]
            loan_id = connection.execute(
                "SELECT id FROM loans WHERE stock_unit_id = ? ORDER BY borrowed_at DESC LIMIT 1",
                (unit_id,),
            ).fetchone()["id"]
            connection.execute(
                "UPDATE stock_units SET current_loan_id = ?, status = 'borrowed' WHERE id = ?",
                (loan_id, unit_id),
            )

        connection.execute(
            "UPDATE stock_units SET status = 'damaged', condition_note = 'Cracked quick-release plate', current_loan_id = NULL WHERE asset_tag = 'TRI-01'"
        )

        connection.commit()
    finally:
        connection.close()


def get_borrowers_for_borrowing():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                u.id,
                u.name,
                u.email,
                (SELECT COUNT(*) FROM loans l WHERE l.borrower_id = u.id AND l.returned_at IS NULL) AS active_loan_count
            FROM users u
            WHERE u.role = 'borrower'
            ORDER BY u.name
            """
        ).fetchall()
    finally:
        connection.close()


def get_active_item_types():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                it.id,
                it.name,
                it.category,
                it.default_loan_days,
                it.deposit_amount,
                it.daily_late_fee,
                (SELECT COUNT(*) FROM stock_units su WHERE su.item_type_id = it.id) AS total_units,
                (SELECT COUNT(*) FROM stock_units su WHERE su.item_type_id = it.id AND su.status = 'available' AND su.current_loan_id IS NULL) AS available_units
            FROM item_types it
            WHERE it.is_active = 1
            ORDER BY it.name
            """
        ).fetchall()
    finally:
        connection.close()


def get_item_type_details(item_type_id):
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                it.id,
                it.name,
                it.category,
                it.default_loan_days,
                it.deposit_amount,
                it.daily_late_fee,
                (SELECT COUNT(*) FROM stock_units su WHERE su.item_type_id = it.id) AS total_units,
                (SELECT COUNT(*) FROM stock_units su WHERE su.item_type_id = it.id AND su.status = 'available' AND su.current_loan_id IS NULL) AS available_units
            FROM item_types it
            WHERE it.id = ? AND it.is_active = 1
            """,
            (item_type_id,),
        ).fetchone()
    finally:
        connection.close()


def get_borrower_active_loan_count(borrower_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE borrower_id = ? AND returned_at IS NULL",
            (borrower_id,),
        ).fetchone()
        return row["count"] if row else 0
    finally:
        connection.close()


def get_available_unit_count(item_type_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM stock_units WHERE item_type_id = ? AND status = 'available' AND current_loan_id IS NULL",
            (item_type_id,),
        ).fetchone()
        return row["count"] if row else 0
    finally:
        connection.close()


def borrow_units_for_request(borrower_id, item_type_id, quantity):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return {"success": False, "message": "Quantity must be a positive integer."}

    if quantity < 1:
        return {"success": False, "message": "Quantity must be a positive integer."}

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        borrower = connection.execute(
            "SELECT id, name, role FROM users WHERE id = ?",
            (borrower_id,),
        ).fetchone()
        if not borrower or borrower["role"] != "borrower":
            connection.rollback()
            return {"success": False, "message": "Invalid borrower selected."}

        item_type = connection.execute(
            "SELECT id, name, default_loan_days, deposit_amount FROM item_types WHERE id = ? AND is_active = 1",
            (item_type_id,),
        ).fetchone()
        if not item_type:
            connection.rollback()
            return {"success": False, "message": "Inactive or nonexistent equipment type."}

        available_count = connection.execute(
            "SELECT COUNT(*) AS count FROM stock_units WHERE item_type_id = ? AND status = 'available' AND current_loan_id IS NULL",
            (item_type_id,),
        ).fetchone()["count"]
        if quantity > available_count:
            connection.rollback()
            return {
                "success": False,
                "message": f"Not enough units available. Requested {quantity}, but only {available_count} are available.",
            }

        current_active_count = connection.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE borrower_id = ? AND returned_at IS NULL",
            (borrower_id,),
        ).fetchone()["count"]
        if current_active_count + quantity > Config.MAX_ACTIVE_LOANS:
            connection.rollback()
            return {
                "success": False,
                "message": (
                    f"Borrowing limit exceeded. This borrower currently has {current_active_count} active item(s), "
                    f"and the maximum is {Config.MAX_ACTIVE_LOANS}."
                ),
            }

        available_units = connection.execute(
            """
            SELECT id, asset_tag
            FROM stock_units
            WHERE item_type_id = ? AND status = 'available' AND current_loan_id IS NULL
            ORDER BY id
            LIMIT ?
            """,
            (item_type_id, quantity),
        ).fetchall()

        if len(available_units) != quantity:
            connection.rollback()
            return {"success": False, "message": "Requested quantity is no longer available. Please try again."}

        borrowed_at = datetime.now()
        due_at = borrowed_at + timedelta(days=item_type["default_loan_days"])
        borrowed_at_text = borrowed_at.strftime("%Y-%m-%d %H:%M:%S")
        due_at_text = due_at.strftime("%Y-%m-%d %H:%M:%S")

        created_loans = []
        total_deposit = 0.0

        for unit in available_units:
            cursor = connection.execute(
                """
                INSERT INTO loans (
                    borrower_id,
                    stock_unit_id,
                    borrowed_at,
                    due_at,
                    returned_at,
                    status,
                    deposit_amount,
                    late_fee_amount,
                    refund_amount,
                    notes
                ) VALUES (?, ?, ?, ?, NULL, 'active', ?, 0, 0, ?)
                """,
                (
                    borrower_id,
                    unit["id"],
                    borrowed_at_text,
                    due_at_text,
                    item_type["deposit_amount"],
                    f"Borrowed by {borrower['name']}",
                ),
            )
            loan_id = cursor.lastrowid
            connection.execute(
                "UPDATE stock_units SET status = 'borrowed', current_loan_id = ? WHERE id = ?",
                (loan_id, unit["id"]),
            )
            total_deposit += float(item_type["deposit_amount"])
            created_loans.append({
                "loan_id": loan_id,
                "asset_tag": unit["asset_tag"],
                "deposit_amount": float(item_type["deposit_amount"]),
            })

        connection.commit()
        return {
            "success": True,
            "message": "Borrowing completed successfully.",
            "borrower_name": borrower["name"],
            "item_name": item_type["name"],
            "quantity": quantity,
            "asset_tags": [loan["asset_tag"] for loan in created_loans],
            "borrowed_at": borrowed_at_text,
            "due_at": due_at_text,
            "total_deposit": total_deposit,
            "loans": created_loans,
        }
    except Exception as exc:
        connection.rollback()
        return {"success": False, "message": f"Database/transaction failure: {exc}"}
    finally:
        connection.close()


def get_dashboard_summary():
    connection = get_connection()
    try:
        total_units = connection.execute("SELECT COUNT(*) AS count FROM stock_units").fetchone()["count"]
        available = connection.execute("SELECT COUNT(*) AS count FROM stock_units WHERE status = 'available' AND current_loan_id IS NULL").fetchone()["count"]
        borrowed = connection.execute("SELECT COUNT(*) AS count FROM stock_units WHERE current_loan_id IS NOT NULL").fetchone()["count"]
        overdue = connection.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE returned_at IS NULL AND due_at < datetime('now')"
        ).fetchone()["count"]
        damaged = connection.execute("SELECT COUNT(*) AS count FROM stock_units WHERE status = 'damaged'").fetchone()["count"]
        lost = connection.execute("SELECT COUNT(*) AS count FROM stock_units WHERE status = 'lost'").fetchone()["count"]
        return {
            "total_units": total_units,
            "available": available,
            "borrowed": borrowed,
            "overdue": overdue,
            "damaged": damaged,
            "lost": lost,
        }
    finally:
        connection.close()


def get_recent_activity(limit=8):
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                u.name AS borrower,
                it.name AS equipment,
                su.asset_tag,
                l.status,
                l.borrowed_at,
                l.due_at,
                l.returned_at
            FROM loans l
            JOIN users u ON u.id = l.borrower_id
            JOIN stock_units su ON su.id = l.stock_unit_id
            JOIN item_types it ON it.id = su.item_type_id
            ORDER BY COALESCE(l.returned_at, l.borrowed_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()


def get_overdue_loans():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                u.name AS borrower,
                it.name AS equipment,
                su.asset_tag,
                l.borrowed_at,
                l.due_at,
                CAST((julianday(datetime('now')) - julianday(l.due_at)) AS INTEGER) AS days_overdue,
                it.daily_late_fee,
                CAST((julianday(datetime('now')) - julianday(l.due_at)) AS INTEGER) * it.daily_late_fee AS estimated_late_fee
            FROM loans l
            JOIN users u ON u.id = l.borrower_id
            JOIN stock_units su ON su.id = l.stock_unit_id
            JOIN item_types it ON it.id = su.item_type_id
            WHERE l.returned_at IS NULL AND l.due_at < datetime('now')
            ORDER BY l.due_at ASC
            """
        ).fetchall()
    finally:
        connection.close()


def get_due_soon_loans():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                u.name AS borrower,
                it.name AS equipment,
                su.asset_tag,
                l.due_at,
                CAST((julianday(l.due_at) - julianday(datetime('now'))) AS INTEGER) AS days_remaining,
                CASE
                    WHEN date(l.due_at) = date('now') THEN 'due_today'
                    ELSE 'due_soon'
                END AS reminder_status
            FROM loans l
            JOIN users u ON u.id = l.borrower_id
            JOIN stock_units su ON su.id = l.stock_unit_id
            JOIN item_types it ON it.id = su.item_type_id
            WHERE l.returned_at IS NULL
              AND l.due_at >= datetime('now')
              AND l.due_at <= datetime('now', '+2 days')
            ORDER BY l.due_at ASC
            """
        ).fetchall()
    finally:
        connection.close()


def get_inventory_summary():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                it.id,
                it.name,
                it.category,
                COUNT(su.id) AS total_units,
                SUM(CASE WHEN su.status = 'available' AND su.current_loan_id IS NULL THEN 1 ELSE 0 END) AS available_units,
                SUM(CASE WHEN su.current_loan_id IS NOT NULL THEN 1 ELSE 0 END) AS borrowed_units,
                SUM(CASE WHEN su.status IN ('damaged', 'lost', 'maintenance') THEN 1 ELSE 0 END) AS damaged_lost_maintenance
            FROM item_types it
            LEFT JOIN stock_units su ON su.item_type_id = it.id
            GROUP BY it.id, it.name, it.category
            ORDER BY it.name
            """
        ).fetchall()
    finally:
        connection.close()


def get_inventory_units():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                su.id,
                it.name AS equipment,
                it.category,
                su.asset_tag,
                su.status,
                su.condition_note,
                u.name AS borrower,
                l.due_at,
                CASE
                    WHEN su.status = 'available' THEN 'Available'
                    WHEN su.status = 'borrowed' THEN 'Borrowed'
                    WHEN su.status = 'overdue' THEN 'Overdue'
                    WHEN su.status = 'damaged' THEN 'Damaged'
                    WHEN su.status = 'lost' THEN 'Lost'
                    WHEN su.status = 'maintenance' THEN 'Maintenance'
                    ELSE 'Unknown'
                END AS status_label
            FROM stock_units su
            JOIN item_types it ON it.id = su.item_type_id
            LEFT JOIN loans l ON l.id = su.current_loan_id
            LEFT JOIN users u ON u.id = l.borrower_id
            ORDER BY it.name, su.asset_tag
            """
        ).fetchall()
    finally:
        connection.close()


def get_active_loans():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT
                l.id,
                u.name AS borrower,
                it.name AS equipment,
                su.asset_tag,
                l.borrowed_at,
                l.due_at,
                CASE
                    WHEN l.returned_at IS NULL AND l.due_at < datetime('now') THEN 'overdue'
                    WHEN l.returned_at IS NULL AND date(l.due_at) = date('now') THEN 'due_today'
                    WHEN l.returned_at IS NULL AND l.due_at <= datetime('now', '+2 days') THEN 'due_soon'
                    WHEN l.returned_at IS NULL THEN 'active'
                    ELSE 'returned'
                END AS loan_status,
                CAST((julianday(datetime('now')) - julianday(l.due_at)) AS INTEGER) AS days_overdue,
                l.deposit_amount
            FROM loans l
            JOIN users u ON u.id = l.borrower_id
            JOIN stock_units su ON su.id = l.stock_unit_id
            JOIN item_types it ON it.id = su.item_type_id
            WHERE l.returned_at IS NULL
            ORDER BY l.due_at ASC
            """
        ).fetchall()
    finally:
        connection.close()


def get_loan_for_return(loan_id):
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT
                l.id,
                u.name AS borrower_name,
                it.name AS equipment_name,
                su.asset_tag,
                l.borrowed_at,
                l.due_at,
                l.returned_at,
                l.deposit_amount,
                it.daily_late_fee,
                CASE
                    WHEN l.returned_at IS NOT NULL THEN 'returned'
                    WHEN l.due_at < datetime('now') THEN 'overdue'
                    ELSE 'active'
                END AS status
            FROM loans l
            JOIN users u ON u.id = l.borrower_id
            JOIN stock_units su ON su.id = l.stock_unit_id
            JOIN item_types it ON it.id = su.item_type_id
            WHERE l.id = ?
            """,
            (loan_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_loan_for_transfer(loan_id):
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT
                l.id,
                l.borrower_id,
                u.name AS borrower_name,
                it.name AS equipment_name,
                su.asset_tag,
                l.stock_unit_id,
                l.borrowed_at,
                l.due_at,
                l.returned_at,
                CASE
                    WHEN l.returned_at IS NOT NULL THEN 'returned'
                    WHEN l.due_at < datetime('now') THEN 'overdue'
                    ELSE 'active'
                END AS status
            FROM loans l
            JOIN users u ON u.id = l.borrower_id
            JOIN stock_units su ON su.id = l.stock_unit_id
            JOIN item_types it ON it.id = su.item_type_id
            WHERE l.id = ?
            """,
            (loan_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def transfer_loan(loan_id, to_borrower_id):
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        loan = connection.execute(
            "SELECT id, borrower_id, returned_at, status FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        if not loan or loan["returned_at"] is not None or loan["status"] not in ("active", "overdue"):
            connection.rollback()
            return {"success": False, "message": "Only an active loan can be transferred."}

        target = connection.execute(
            "SELECT id, name, role FROM users WHERE id = ?",
            (to_borrower_id,),
        ).fetchone()
        if not target or target["role"] != "borrower":
            connection.rollback()
            return {"success": False, "message": "Invalid target borrower selected."}

        if target["id"] == loan["borrower_id"]:
            connection.rollback()
            return {"success": False, "message": "The target borrower must be different from the current borrower."}

        target_active_count = connection.execute(
            "SELECT COUNT(*) AS count FROM loans WHERE borrower_id = ? AND returned_at IS NULL",
            (to_borrower_id,),
        ).fetchone()["count"]
        if target_active_count >= Config.MAX_ACTIVE_LOANS:
            connection.rollback()
            return {
                "success": False,
                "message": (
                    f"Transfer rejected. {target['name']} already has {target_active_count} active item(s), "
                    f"and the maximum is {Config.MAX_ACTIVE_LOANS}."
                ),
            }

        connection.execute(
            "UPDATE loans SET borrower_id = ? WHERE id = ?",
            (to_borrower_id, loan_id),
        )
        connection.execute(
            """
            INSERT INTO loan_transfers (loan_id, from_borrower_id, to_borrower_id)
            VALUES (?, ?, ?)
            """,
            (loan_id, loan["borrower_id"], to_borrower_id),
        )
        connection.commit()
        return {
            "success": True,
            "loan_id": loan_id,
            "from_borrower_id": loan["borrower_id"],
            "to_borrower_id": to_borrower_id,
            "to_borrower_name": target["name"],
        }
    except Exception as exc:
        connection.rollback()
        return {"success": False, "message": f"Transfer failed: {exc}"}
    finally:
        connection.close()
