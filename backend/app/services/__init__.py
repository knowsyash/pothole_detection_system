"""Services package."""

from app.services.storage import StorageService, storage_service
from app.services.authorities import CivicAuthority, resolve_authority, list_authorities, get_authority_by_code
from app.services.reporting import generate_pothole_report, dispatch_report, generate_ticket_id
from app.services.email_service import EmailService, email_service

__all__ = [
    "StorageService",
    "storage_service",
    "CivicAuthority",
    "resolve_authority",
    "list_authorities",
    "get_authority_by_code",
    "generate_pothole_report",
    "dispatch_report",
    "generate_ticket_id",
    "EmailService",
    "email_service",
]

