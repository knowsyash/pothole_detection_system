"""Civic reporting service: report generation, real email dispatch, and authority API simulation."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.models.pothole import PotholeRecord, ReportChannel, ReportStatus
from app.services.authorities import CivicAuthority, resolve_authority, get_authority_by_code


def generate_ticket_id(authority_code: str) -> str:
    """Generate a clean, human-readable municipal ticket ID."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"TKT-{authority_code}-{date_str}-{unique_suffix}"


def generate_pothole_report(
    pothole: PotholeRecord,
    authority: Optional[CivicAuthority] = None,
    custom_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a comprehensive incident report for a detected pothole."""
    if authority is None:
        authority = resolve_authority(pothole.latitude, pothole.longitude)

    ticket_id = pothole.ticket_id or generate_ticket_id(authority.code)
    maps_url = f"https://www.google.com/maps?q={pothole.latitude},{pothole.longitude}"

    # Format ISO timestamp
    ts_str = pothole.timestamp.isoformat() if hasattr(pothole.timestamp, "isoformat") else str(pothole.timestamp)

    # Subject line
    is_urgent = pothole.severity in ("CRITICAL", "HIGH")
    urgency_tag = "[URGENT HAZARD]" if is_urgent else "[ROAD INCIDENT]"
    subject = f"{urgency_tag} Pothole Report {ticket_id} ({pothole.severity}) - {authority.code}"

    # Plain text email body
    text_body = f"""================================================================
okDRIVER MUNICIPAL ROAD INCIDENT REPORT
Ticket ID: {ticket_id}
Status: PENDING CIVIC INSPECTION
================================================================

ATTENTION: {authority.name}
Department Contact: {authority.contact_email}
Target System: {authority.api_endpoint}

INCIDENT SUMMARY:
-----------------
Pothole ID:           {pothole.id}
Severity Level:       {pothole.severity} (Score: {pothole.severity_score}/10.0)
Detection Confidence: {round(pothole.confidence * 100, 1)}%
Detection Time:       {ts_str}

GEOGRAPHIC LOCATION:
--------------------
Latitude:             {pothole.latitude}
Longitude:            {pothole.longitude}
Altitude:             {pothole.altitude or 'N/A'} m
Vehicle Speed:        {pothole.speed_kmh or 'N/A'} km/h
Google Maps Link:     {maps_url}

IMAGE EVIDENCE:
---------------
Annotated Overlay:    {pothole.annotated_evidence_url or 'N/A'}
Raw Image Evidence:   {pothole.image_evidence_url or 'N/A'}

ADDITIONAL NOTES:
-----------------
{custom_notes or pothole.notes or 'Automated computer vision detection by okDRIVER system.'}

================================================================
Generated automatically by okDRIVER Telemetry & Pothole Detection Suite.
"""

    # Rich HTML email body
    severity_color = {
        "CRITICAL": "#dc2626",
        "HIGH": "#ea580c",
        "MEDIUM": "#ca8a04",
        "LOW": "#16a34a",
    }.get(pothole.severity, "#4b5563")

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; margin: 0; padding: 20px; }}
    .container {{ max-width: 650px; margin: 0 auto; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .header {{ background: #111827; color: #ffffff; padding: 24px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-weight: bold; font-size: 14px; color: #fff; background: {severity_color}; }}
    .content {{ padding: 24px; }}
    .section {{ margin-bottom: 20px; border-bottom: 1px solid #f3f4f6; padding-bottom: 16px; }}
    .field-label {{ font-weight: 600; color: #4b5563; min-width: 140px; display: inline-block; }}
    .button {{ display: inline-block; background: #2563eb; color: #ffffff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 500; margin-top: 8px; }}
    .footer {{ background: #f9fafb; padding: 16px; font-size: 12px; color: #6b7280; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin: 0 0 8px 0;">okDRIVER Municipal Road Hazard Report</h2>
      <div>Ticket ID: <strong>{ticket_id}</strong> | <span class="badge">{pothole.severity} HAZARD</span></div>
    </div>
    <div class="content">
      <div class="section">
        <h3 style="margin-top: 0;">Jurisdiction &amp; Authority</h3>
        <div><span class="field-label">Assigned Authority:</span> <strong>{authority.name}</strong></div>
        <div><span class="field-label">Department Code:</span> {authority.code}</div>
        <div><span class="field-label">Contact Email:</span> {authority.contact_email}</div>
      </div>
      <div class="section">
        <h3>Detection &amp; Telemetry</h3>
        <div><span class="field-label">Severity Rating:</span> <strong>{pothole.severity}</strong> (Score: {pothole.severity_score}/10.0)</div>
        <div><span class="field-label">Confidence:</span> {round(pothole.confidence * 100, 1)}%</div>
        <div><span class="field-label">Detection Time:</span> {ts_str}</div>
        <div><span class="field-label">Coordinates:</span> {pothole.latitude}, {pothole.longitude}</div>
        <p><a href="{maps_url}" target="_blank" class="button">View on Google Maps</a></p>
      </div>
      <div class="section">
        <h3>Evidence &amp; Inspection</h3>
        <div><span class="field-label">Annotated Frame:</span> {pothole.annotated_evidence_url or 'None'}</div>
        <div><span class="field-label">Raw Photo:</span> {pothole.image_evidence_url or 'None'}</div>
        <p style="color: #6b7280; font-style: italic;">{custom_notes or pothole.notes or 'Recorded automatically by okDRIVER fleet vehicle sensor.'}</p>
      </div>
    </div>
    <div class="footer">
      Automated road inspection dispatch &copy; 2026 okDRIVER. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    return {
        "ticket_id": ticket_id,
        "pothole_id": pothole.id,
        "authority": {
            "code": authority.code,
            "name": authority.name,
            "region": authority.region,
            "contact_email": authority.contact_email,
            "api_endpoint": authority.api_endpoint,
        },
        "location": {
            "latitude": pothole.latitude,
            "longitude": pothole.longitude,
            "altitude": pothole.altitude,
            "speed_kmh": pothole.speed_kmh,
            "heading_deg": pothole.heading_deg,
            "location_name": getattr(pothole, "location_name", None) or getattr(authority, "location_name", None) or authority.region,
            "city_district": getattr(pothole, "city_district", None) or getattr(authority, "city", None) or authority.region,
            "maps_url": maps_url,
        },
        "detection": {
            "timestamp": ts_str,
            "severity": pothole.severity,
            "severity_score": pothole.severity_score,
            "confidence": pothole.confidence,
            "bounding_box": pothole.bounding_box,
        },
        "evidence": {
            "image_evidence_url": pothole.image_evidence_url,
            "annotated_evidence_url": pothole.annotated_evidence_url,
        },
        "email_payload": {
            "subject": subject,
            "to": authority.contact_email,
            "body_text": text_body,
            "body_html": html_body,
        },
    }


def dispatch_report(report_data: Dict[str, Any], channel: str = "SIMULATED_API") -> Dict[str, Any]:
    """
    Dispatch a report through the specified channel.

    Channels:
    - EMAIL          → sends a real email via Gmail SMTP (falls back to simulated if unconfigured)
    - SIMULATED_API  → returns a mock authority API response (no network call)
    """
    from app.services.email_service import email_service  # lazy import to avoid circular deps

    ticket_id = report_data["ticket_id"]
    authority = report_data["authority"]
    now_iso = datetime.now(timezone.utc).isoformat()
    sla_hours = 24 if report_data["detection"]["severity"] in ("CRITICAL", "HIGH") else 48

    if channel in (ReportChannel.EMAIL.value, "EMAIL"):
        email_payload = report_data["email_payload"]
        result = email_service.send(
            to=email_payload["to"],
            subject=email_payload["subject"],
            body_text=email_payload["body_text"],
            body_html=email_payload["body_html"],
        )

        return {
            "channel": ReportChannel.EMAIL.value,
            "status": ReportStatus.REPORTED.value,
            "delivered": result.get("delivered", False),
            "recipient": authority["contact_email"],
            "subject": email_payload["subject"],
            "message_id": result.get("message_id"),
            "dispatched_at": now_iso,
            "response_message": (
                f"Email delivered to {authority['contact_email']}"
                if result.get("delivered")
                else f"Email delivery failed: {result.get('error')}"
            ),
            "sla_resolution_target_hours": sla_hours,
            "simulated": result.get("simulated", False),
            "error": result.get("error"),
        }

    elif channel in (ReportChannel.TELEGRAM.value, "TELEGRAM"):
        from app.services.telegram_service import telegram_service
        result = telegram_service.send_pothole_alert(report_data)
        is_ok = result.get("delivered", False)
        return {
            "channel": ReportChannel.TELEGRAM.value,
            "status": ReportStatus.REPORTED.value if is_ok else ReportStatus.FAILED.value,
            "delivered": is_ok,
            "recipient": f"Telegram Chat ({result.get('chat_id') or '@okdriver_bot'})",
            "subject": f"Telegram Alert {ticket_id}",
            "message_id": result.get("message_id"),
            "dispatched_at": now_iso,
            "response_message": (
                f"Telegram alert sent to Chat {result.get('chat_id')}!"
                if is_ok
                else f"Telegram delivery note: {result.get('error')}"
            ),
            "sla_resolution_target_hours": sla_hours,
            "error": result.get("error"),
        }

    else:
        # Default: Simulate Authority API submission
        external_id = f"EXT-{authority['code']}-{uuid.uuid4().hex[:8].upper()}"
        return {
            "channel": ReportChannel.SIMULATED_API.value,
            "status": ReportStatus.ACKNOWLEDGED.value,
            "delivered": True,
            "http_status_code": 201,
            "target_endpoint": authority["api_endpoint"],
            "external_reference_id": external_id,
            "dispatched_at": now_iso,
            "acknowledged": True,
            "response_message": f"Authority API ({authority['code']}) acknowledged ticket {ticket_id}.",
            "sla_resolution_target_hours": sla_hours,
        }
