"""Telegram alerting service for dispatching instant civic road distress alerts."""

import html
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.config import settings

logger = logging.getLogger("okdriver.telegram")


class TelegramService:
    """Service to deliver live civic incident alerts via Telegram Bot API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "8837174299:AAGbvuRoW8h13Wt46Dhz_T_TN0x4MCbWNSc")
        self.api_base = f"https://api.telegram.org/bot{self.token}"

    def get_latest_chat_id(self) -> Optional[int]:
        """Poll Telegram getUpdates to find the most recent chat ID that started or messaged the bot."""
        default_chat_id = getattr(settings, "TELEGRAM_DEFAULT_CHAT_ID", None)
        if default_chat_id:
            return int(default_chat_id)

        try:
            url = f"{self.api_base}/getUpdates"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok") and data.get("result"):
                    # Find the last update with a message or callback_query
                    for item in reversed(data["result"]):
                        msg = item.get("message") or item.get("edited_message") or item.get("channel_post")
                        if msg and "chat" in msg:
                            return msg["chat"]["id"]
        except Exception as exc:
            logger.warning(f"Failed to fetch Telegram getUpdates: {exc}")
        return None

    def send_message(
        self,
        text: str,
        chat_id: Optional[int | str] = None,
        reply_markup: Optional[dict] = None,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        """Send a formatted text message to Telegram chat."""
        target_chat = chat_id or self.get_latest_chat_id()
        if not target_chat:
            return {
                "delivered": False,
                "error": "No Telegram chat_id found. Please open @okdriver_bot in Telegram and tap 'Start'.",
                "chat_id": None,
            }

        payload: Dict[str, Any] = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            url = f"{self.api_base}/sendMessage"
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("ok"):
                    return {
                        "delivered": True,
                        "chat_id": target_chat,
                        "message_id": res_data["result"]["message_id"],
                    }
                else:
                    return {
                        "delivered": False,
                        "error": res_data.get("description", "Unknown Telegram API error"),
                        "chat_id": target_chat,
                    }
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            logger.warning(f"Telegram dispatch warning: {exc} - Body: {err_body}")

            # Fallback 1: If Telegram rejected an inline keyboard URL (e.g. localhost), retry without the offending button
            if reply_markup and "Wrong HTTP URL" in err_body:
                safe_keyboard = []
                for row in reply_markup.get("inline_keyboard", []):
                    # Filter out any button with localhost or invalid protocol
                    safe_row = [btn for btn in row if "localhost" not in btn.get("url", "")]
                    if safe_row:
                        safe_keyboard.append(safe_row)
                return self.send_message(
                    text=text,
                    chat_id=target_chat,
                    reply_markup={"inline_keyboard": safe_keyboard} if safe_keyboard else None,
                    parse_mode=parse_mode,
                )

            # Fallback 2: If HTML parsing failed, retry as plain text without parse_mode
            if parse_mode and "can't parse entities" in err_body:
                # Strip basic tags
                plain_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
                return self.send_message(
                    text=plain_text,
                    chat_id=target_chat,
                    reply_markup=reply_markup,
                    parse_mode="",
                )

            return {
                "delivered": False,
                "error": f"{exc} - {err_body}",
                "chat_id": target_chat,
            }
        except Exception as exc:
            logger.error(f"Telegram dispatch failed: {exc}")
            return {
                "delivered": False,
                "error": str(exc),
                "chat_id": target_chat,
            }

    def send_pothole_alert(
        self,
        report_data: Dict[str, Any],
        chat_id: Optional[int | str] = None,
    ) -> Dict[str, Any]:
        """Format and dispatch a structured pothole incident alert to Telegram."""
        ticket_id = report_data.get("ticket_id", "N/A")
        det = report_data.get("detection", {})
        loc = report_data.get("location", {})
        auth = report_data.get("authority", {})

        severity = det.get("severity", "MEDIUM")
        score = det.get("severity_score", 0.0)
        confidence = round((det.get("confidence") or 0.0) * 100, 1)
        lat = loc.get("latitude", 0.0)
        lon = loc.get("longitude", 0.0)
        street = loc.get("location_name") or loc.get("city_district") or f"{lat:.4f}, {lon:.4f}"
        auth_name = auth.get("name") or "Municipal Works Dept"
        auth_code = auth.get("code") or "PWD"

        # Escape HTML entities in dynamic fields
        safe_ticket_id = html.escape(str(ticket_id))
        safe_street = html.escape(str(street))
        safe_auth_name = html.escape(str(auth_name))
        safe_auth_code = html.escape(str(auth_code))

        sla_str = "&lt; 24 Hours (Urgent)" if severity in ("CRITICAL", "HIGH") else "&lt; 48 Hours"
        severity_icon = "🔴" if severity == "CRITICAL" else "🟠" if severity == "HIGH" else "🟡"
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"

        # Telegram rejects 'localhost' in inline keyboard button URLs.
        # We ensure it resolves to 127.0.0.1 or configured FRONTEND_URL.
        frontend_base = getattr(settings, "FRONTEND_URL", "http://127.0.0.1:3000")
        if "localhost" in frontend_base:
            frontend_base = frontend_base.replace("localhost", "127.0.0.1")
        dossier_url = f"{frontend_base.rstrip('/')}/potholes/{report_data.get('pothole_id', '')}"

        caption = (
            f"🚨 <b>okDRIVER ROAD HAZARD ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎫 <b>Ticket Reference:</b> <code>{safe_ticket_id}</code>\n"
            f"{severity_icon} <b>Severity:</b> <b>{severity} HAZARD</b> (Score: {score}/10)\n"
            f"📍 <b>Location:</b> <b>{safe_street}</b>\n"
            f"🏛️ <b>Assigned Civic Authority:</b>\n"
            f"    {safe_auth_name} (<code>{safe_auth_code}</code>)\n"
            f"🎯 <b>AI Detection Confidence:</b> {confidence}%\n"
            f"🛰️ <b>GPS Coordinates:</b> <code>{lat:.6f}, {lon:.6f}</code>\n"
            f"⏱️ <b>Target SLA:</b> {sla_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <i>Automated telemetry alert logged by okDRIVER Vision Fleet.</i>"
        )

        # Inline Action Buttons
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🗺️ Open in Google Maps", "url": maps_url},
                    {"text": "🌐 View Incident Dossier", "url": dossier_url},
                ]
            ]
        }

        return self.send_message(
            text=caption,
            chat_id=chat_id,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


telegram_service = TelegramService()
