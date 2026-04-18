from __future__ import annotations

import html
import logging
import os
import smtplib
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.incident_repository import IncidentRepository


logger = logging.getLogger(__name__)


class EmailSendError(RuntimeError):
    pass


class EmailNotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = IncidentRepository(db)

    def send_manager_notification_for_incident(self, incident_id: UUID) -> bool:
        """
        Look up the processed incident, build email content, and send
        an email to the manager. Return True on success, False on failure.
        Raise a custom exception or ValueError if the incident does not exist.
        """
        processed_incident = self.repository.get_processed_incident(incident_id)
        if processed_incident is None:
            raise ValueError("Processed incident not found")

        subject, text_body, html_body = self._build_incident_email_content(processed_incident)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._setting("SMTP_FROM", "no-reply@example.com")
        msg["To"] = self._setting("MANAGER_EMAIL_DEFAULT", "manager@example.com")
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        host = self._setting("SMTP_HOST", "localhost")
        port = int(self._setting("SMTP_PORT", 25))
        username = self._setting("SMTP_USERNAME", None)
        password = self._setting("SMTP_PASSWORD", None)
        use_tls = self._as_bool(self._setting("SMTP_USE_TLS", True), default=True)

        try:
            with smtplib.SMTP(host, port) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            return True
        except smtplib.SMTPException as exc:
            logger.exception("Failed to send manager notification for incident %s", incident_id)
            raise EmailSendError("Failed to send manager notification") from exc
        except Exception as exc:
            logger.exception("Unexpected error while sending manager notification for incident %s", incident_id)
            raise EmailSendError("Failed to send manager notification") from exc

    def _build_incident_email_content(self, processed_incident) -> tuple[str, str, str]:
        """
        Returns (subject, text_body, html_body).
        """
        incident = getattr(processed_incident, "incident", None)

        site = self._first_non_empty(
            self._stringify(getattr(incident, "site", None)),
            self._stringify(getattr(incident, "location", None)),
        )
        country = self._stringify(getattr(incident, "country", None))
        occurred_at = self._format_datetime(getattr(incident, "occurred_at", None))
        title = self._stringify(getattr(incident, "title", None))
        description = self._stringify(getattr(incident, "description", None))

        hazard_category = self._stringify(getattr(processed_incident, "hazard_category", None))
        cause_category = self._stringify(getattr(processed_incident, "cause_category", None))
        severity = self._stringify(getattr(processed_incident, "severity_level", None))
        recurrence = self._stringify(getattr(processed_incident, "recurrence_frequency", None))
        risk_score = getattr(processed_incident, "risk_score", None)
        risk_score_text = self._stringify(risk_score)
        risk_label = self._stringify(getattr(processed_incident, "risk_level_label", None))
        recommendation_summary = self._stringify(getattr(processed_incident, "recommendation_summary", None))
        recommended_actions = self._extract_recommended_actions(recommendation_summary)

        subject = f"[Safety] {risk_label} risk incident at {site} (score {risk_score_text})"

        text_lines = [
            "Safety incident summary for management",
            f"Site: {site}",
            f"Country: {country}",
            f"Occurred at: {occurred_at}",
            f"Title: {title}",
            f"Description: {description}",
            f"Hazard category: {hazard_category}",
            f"Cause category: {cause_category}",
            f"Severity: {severity}",
            f"Recurrence: {recurrence}",
            f"Risk score: {risk_score_text}",
            f"Risk label: {risk_label}",
            f"Recommendation summary: {recommendation_summary}",
        ]
        if recommended_actions:
            text_lines.append(f"Key recommended actions: {recommended_actions}")
        text_lines.append("")
        text_lines.append("This email was generated automatically by the AI Safety Intelligence layer.")
        text_body = "\n".join(text_lines)

        html_body = """
        <html>
          <body style="font-family: Arial, Helvetica, sans-serif; color: #1f2937; line-height: 1.5;">
            <div style="max-width: 760px; margin: 0 auto; padding: 24px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;">
              <h2 style="margin: 0 0 16px; color: #0f172a;">Safety incident summary for management</h2>
              <p style="margin: 0 0 12px;"><strong>Site:</strong> {site}</p>
              <p style="margin: 0 0 12px;"><strong>Country:</strong> {country}</p>
              <p style="margin: 0 0 12px;"><strong>Occurred at:</strong> {occurred_at}</p>
              <p style="margin: 0 0 12px;"><strong>Title:</strong> {title}</p>
              <p style="margin: 0 0 12px;"><strong>Description:</strong> {description}</p>
              <p style="margin: 0 0 12px;"><strong>Hazard category:</strong> {hazard_category}</p>
              <p style="margin: 0 0 12px;"><strong>Cause category:</strong> {cause_category}</p>
              <p style="margin: 0 0 12px;"><strong>Severity:</strong> {severity}</p>
              <p style="margin: 0 0 12px;"><strong>Recurrence:</strong> {recurrence}</p>
              <p style="margin: 0 0 12px;"><strong>Risk score:</strong> {risk_score_text}</p>
              <p style="margin: 0 0 12px;"><strong>Risk label:</strong> {risk_label}</p>
              <p style="margin: 0 0 12px;"><strong>Recommendation summary:</strong> {recommendation_summary}</p>
              <p style="margin: 0 0 12px;"><strong>Key recommended actions:</strong> {recommended_actions}</p>
              <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0;" />
              <p style="margin: 0; font-size: 12px; color: #6b7280;">This email was generated automatically by the AI Safety Intelligence layer.</p>
            </div>
          </body>
        </html>
        """.format(
            site=html.escape(site),
            country=html.escape(country),
            occurred_at=html.escape(occurred_at),
            title=html.escape(title),
            description=html.escape(description),
            hazard_category=html.escape(hazard_category),
            cause_category=html.escape(cause_category),
            severity=html.escape(severity),
            recurrence=html.escape(recurrence),
            risk_score_text=html.escape(risk_score_text),
            risk_label=html.escape(risk_label),
            recommendation_summary=html.escape(recommendation_summary),
            recommended_actions=html.escape(recommended_actions or "Unknown"),
        )

        return subject, text_body, html_body

    @staticmethod
    def _setting(name: str, default):
        value = getattr(settings, name, None)
        if value is not None:
            return value
        return os.getenv(name, default)

    @staticmethod
    def _as_bool(value, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _stringify(value) -> str:
        if value is None:
            return "Unknown"
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else "Unknown"
        return str(value)

    @staticmethod
    def _first_non_empty(*values: str) -> str:
        for value in values:
            if value and value != "Unknown":
                return value
        return "Unknown"

    @staticmethod
    def _format_datetime(value) -> str:
        if value is None:
            return "Unknown"
        iso_value = getattr(value, "isoformat", None)
        if callable(iso_value):
            return str(iso_value(sep=" "))
        return str(value)

    @staticmethod
    def _extract_recommended_actions(recommendation_summary: str) -> str:
        if not recommendation_summary or recommendation_summary == "Unknown":
            return "Unknown"

        summary = recommendation_summary.strip()
        for prefix in ("Summary:", "Recommendation:", "Actions:"):
            if summary.lower().startswith(prefix.lower()):
                summary = summary[len(prefix):].strip()
                break

        return summary if summary else "Unknown"