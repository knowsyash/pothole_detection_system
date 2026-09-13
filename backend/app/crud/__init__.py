"""CRUD operations package."""

from app.crud.pothole import (
    create_pothole,
    create_potholes_bulk,
    get_pothole_by_id,
    get_potholes,
    update_pothole,
    delete_pothole,
    get_pothole_stats,
    create_pothole_report,
    get_report_by_ticket_id,
    get_reports,
    get_unreported_potholes,
)

__all__ = [
    "create_pothole",
    "create_potholes_bulk",
    "get_pothole_by_id",
    "get_potholes",
    "update_pothole",
    "delete_pothole",
    "get_pothole_stats",
    "create_pothole_report",
    "get_report_by_ticket_id",
    "get_reports",
    "get_unreported_potholes",
]
