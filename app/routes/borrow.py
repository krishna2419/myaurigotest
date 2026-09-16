from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.config import Config
from app.db import borrow_units_for_request, get_active_item_types, get_borrowers_for_borrowing, get_item_type_details

bp = Blueprint("borrow", __name__)


@bp.route("/borrow", methods=["GET", "POST"])
def borrow():
    item_types = get_active_item_types()
    borrowers = get_borrowers_for_borrowing()
    selection = None
    item_details = None
    borrower_details = None

    if request.method == "POST":
        borrower_id = request.form.get("borrower_id")
        item_type_id = request.form.get("item_type_id")
        quantity = request.form.get("quantity")

        if not borrower_id:
            flash("Please select a borrower.", "error")
        elif not item_type_id:
            flash("Please select equipment.", "error")
        else:
            try:
                borrower_id = int(borrower_id)
                item_type_id = int(item_type_id)
                quantity = int(quantity or 0)
            except (TypeError, ValueError):
                flash("Borrower, equipment, and quantity must be valid.", "error")
                borrower_id = None
                item_type_id = None
                quantity = 0

            if borrower_id is not None and item_type_id is not None:
                result = borrow_units_for_request(borrower_id, item_type_id, quantity)
                if result["success"]:
                    return render_template(
                        "borrow_success.html",
                        borrower_name=result["borrower_name"],
                        item_name=result["item_name"],
                        quantity=result["quantity"],
                        asset_tags=result["asset_tags"],
                        borrowed_at=result["borrowed_at"],
                        due_at=result["due_at"],
                        total_deposit=result["total_deposit"],
                        current_page="borrow",
                    )
                flash(result["message"], "error")

        selection = {
            "borrower_id": borrower_id,
            "item_type_id": item_type_id,
            "quantity": quantity,
        }
        if item_type_id:
            item_details = get_item_type_details(item_type_id)
        if borrower_id:
            borrower_details = next((b for b in borrowers if b["id"] == borrower_id), None)

    if request.method == "GET":
        item_types = [dict(item) for item in item_types]
        for item in item_types:
            item["available_units"] = item["available_units"] if item["available_units"] is not None else 0

    return render_template(
        "borrow.html",
        borrowers=borrowers,
        item_types=item_types,
        selection=selection,
        item_details=item_details,
        borrower_details=borrower_details,
        max_active_loans=Config.MAX_ACTIVE_LOANS,
        current_page="borrow",
    )
