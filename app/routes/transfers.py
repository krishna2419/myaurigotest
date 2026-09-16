from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.config import Config
from app.db import get_borrowers_for_borrowing, get_loan_for_transfer, transfer_loan

bp = Blueprint("transfer", __name__)


@bp.route("/transfer/<int:loan_id>", methods=["GET", "POST"])
def transfer_item(loan_id):
    loan = get_loan_for_transfer(loan_id)
    if not loan:
        abort(404)

    borrowers = [borrower for borrower in get_borrowers_for_borrowing() if borrower["id"] != loan["borrower_id"]]
    if loan["status"] not in ("active", "overdue"):
        flash("Only an active loan can be transferred.", "error")
        return redirect(url_for("dashboard.loans"))

    if request.method == "GET":
        return render_template("transfer.html", loan=loan, borrowers=borrowers, max_active_loans=Config.MAX_ACTIVE_LOANS, current_page="loans")

    target_borrower_id = request.form.get("to_borrower_id")
    try:
        target_borrower_id = int(target_borrower_id)
    except (TypeError, ValueError):
        target_borrower_id = None

    if target_borrower_id is None:
        flash("Please select a valid target borrower.", "error")
        return render_template("transfer.html", loan=loan, borrowers=borrowers, max_active_loans=Config.MAX_ACTIVE_LOANS, current_page="loans")

    result = transfer_loan(loan_id, target_borrower_id)
    if not result["success"]:
        flash(result["message"], "error")
        return render_template("transfer.html", loan=loan, borrowers=borrowers, max_active_loans=Config.MAX_ACTIVE_LOANS, current_page="loans")

    return render_template(
        "transfer_success.html",
        loan=loan,
        new_borrower_name=result["to_borrower_name"],
        current_page="loans",
    )
