from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.db import get_connection, get_loan_for_return

bp = Blueprint("return", __name__)


@bp.route("/return/<int:loan_id>", methods=["GET", "POST"])
def return_item(loan_id):
    loan = get_loan_for_return(loan_id)
    if not loan:
        abort(404)

    if loan["status"] != "active" and loan["status"] != "overdue":
        flash("This loan has already been returned or is not active.", "error")
        return redirect(url_for("dashboard.loans"))

    if request.method == "GET":
        return render_template(
            "return.html",
            loan=loan,
            current_page="loans",
        )

    condition = request.form.get("condition", "Good")
    if condition not in ["Good", "Damaged", "Lost"]:
        flash("Please select a valid return condition.", "error")
        return render_template(
            "return.html",
            loan=loan,
            current_page="loans",
        )

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        active_loan = connection.execute(
            "SELECT * FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        if not active_loan:
            connection.rollback()
            flash("Loan not found.", "error")
            return redirect(url_for("dashboard.loans"))

        if active_loan["returned_at"] is not None:
            connection.rollback()
            flash("This loan has already been returned.", "error")
            return redirect(url_for("dashboard.loans"))

        stock_unit = connection.execute(
            "SELECT * FROM stock_units WHERE id = ?",
            (active_loan["stock_unit_id"],),
        ).fetchone()
        if not stock_unit:
            connection.rollback()
            flash("The linked stock unit does not exist.", "error")
            return redirect(url_for("dashboard.loans"))

        if stock_unit["current_loan_id"] != loan_id:
            connection.rollback()
            flash("The stock unit is no longer linked to this active loan.", "error")
            return redirect(url_for("dashboard.loans"))

        return_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        due_at = datetime.strptime(active_loan["due_at"], "%Y-%m-%d %H:%M:%S")
        return_dt = datetime.strptime(return_time, "%Y-%m-%d %H:%M:%S")
        late_days = max(0, (return_dt - due_at).days)
        late_fee = float(active_loan["deposit_amount"]) * 0

        item_type = connection.execute(
            "SELECT daily_late_fee FROM item_types WHERE id = (SELECT item_type_id FROM stock_units WHERE id = ?)",
            (active_loan["stock_unit_id"],),
        ).fetchone()
        if item_type is not None:
            late_fee = max(0.0, float(late_days) * float(item_type["daily_late_fee"]))

        refund_amount = max(0.0, float(active_loan["deposit_amount"]) - late_fee)

        if condition == "Good":
            stock_status = "available"
        elif condition == "Damaged":
            stock_status = "damaged"
        else:
            stock_status = "lost"

        connection.execute(
            """
            UPDATE loans
            SET returned_at = ?, status = 'returned', late_fee_amount = ?, refund_amount = ?, notes = COALESCE(notes, '') || ?
            WHERE id = ?
            """,
            (
                return_time,
                late_fee,
                refund_amount,
                f" | Return condition: {condition}",
                loan_id,
            ),
        )

        connection.execute(
            "UPDATE stock_units SET status = ?, current_loan_id = NULL WHERE id = ?",
            (stock_status, active_loan["stock_unit_id"]),
        )

        connection.commit()

        return render_template(
            "return_success.html",
            borrower_name=loan["borrower_name"],
            equipment_name=loan["equipment_name"],
            asset_tag=loan["asset_tag"],
            borrowed_at=loan["borrowed_at"],
            due_at=loan["due_at"],
            returned_at=return_time,
            late_days=late_days,
            late_fee=late_fee,
            original_deposit=active_loan["deposit_amount"],
            refund_amount=refund_amount,
            condition=condition,
            current_page="loans",
        )
    except Exception as exc:
        connection.rollback()
        flash(f"Return failed: {exc}", "error")
        return redirect(url_for("dashboard.loans"))
    finally:
        connection.close()
