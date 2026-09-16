from flask import Blueprint, render_template

from app.db import get_active_loans, get_dashboard_summary, get_due_soon_loans, get_inventory_summary, get_inventory_units, get_overdue_loans, get_recent_activity

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    summary = get_dashboard_summary()
    recent_activity = get_recent_activity()
    overdue_loans = get_overdue_loans()
    due_soon_loans = get_due_soon_loans()
    return render_template(
        "dashboard.html",
        summary=summary,
        recent_activity=recent_activity,
        overdue_loans=overdue_loans,
        due_soon_loans=due_soon_loans,
        current_page="dashboard",
    )


@bp.route("/equipment")
def equipment():
    inventory_summary = get_inventory_summary()
    inventory_units = get_inventory_units()
    return render_template(
        "equipment.html",
        inventory_summary=inventory_summary,
        inventory_units=inventory_units,
        current_page="equipment",
    )


@bp.route("/loans")
def loans():
    active_loans = get_active_loans()
    return render_template(
        "loans.html",
        active_loans=active_loans,
        current_page="loans",
    )


@bp.route("/overdue")
def overdue():
    return render_template(
        "overdue.html",
        overdue_loans=get_overdue_loans(),
        current_page="overdue",
    )
