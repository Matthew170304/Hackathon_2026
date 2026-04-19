from __future__ import annotations

from html import escape

from pydantic import BaseModel
import httpx

from app.core.config import get_settings
from app.schemas.analytics_schemas import StrategicRecommendation


MAILTRAP_AUTH_HEADER_PREFIX = "Bearer"
MAILTRAP_SUCCESS_STATUS_CODES = {200, 201, 202}
DEFAULT_TIMEOUT_SECONDS = 10.0
EMAIL_GRAPH_PRIORITY_LIMIT = 5
EMAIL_ACTION_LIMIT = 4

PRIORITY_COLORS = {
    "Critical": "#dc2626",
    "High": "#f97316",
    "Medium": "#ca8a04",
    "Low": "#16a34a",
    "Review": "#2563eb",
}
DEFAULT_PRIORITY_COLOR = "#2563eb"


class MailResult(BaseModel):
    sent: bool
    status_code: int | None = None
    response_text: str | None = None


class MailService:
    def __init__(
        self,
        api_token: str | None = None,
        sender_email: str | None = None,
        sender_name: str | None = None,
        api_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_token = settings.mailtrap_api_token if api_token is None else api_token
        self.sender_email = settings.mailtrap_sender_email if sender_email is None else sender_email
        self.sender_name = settings.mailtrap_sender_name if sender_name is None else sender_name
        self.default_recipient_email = settings.mailtrap_default_recipient_email
        self.api_url = settings.mailtrap_api_url if api_url is None else api_url
        self.http_client = http_client

    async def send_email(
        self,
        subject: str,
        text: str,
        to_email: str | None = None,
        to_name: str | None = None,
        html: str | None = None,
        category: str | None = None,
    ) -> MailResult:
        self._validate_configuration()

        payload = self._build_payload(
            to_email=to_email or self.default_recipient_email,
            to_name=to_name,
            subject=subject,
            text=text,
            html=html,
            category=category,
        )
        headers = {
            "Authorization": f"{MAILTRAP_AUTH_HEADER_PREFIX} {self.api_token}",
            "Content-Type": "application/json",
        }

        if self.http_client is not None:
            response = await self.http_client.post(self.api_url, json=payload, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)

        return MailResult(
            sent=response.status_code in MAILTRAP_SUCCESS_STATUS_CODES,
            status_code=response.status_code,
            response_text=response.text,
        )

    async def send_strategic_recommendation(
        self,
        recommendation: StrategicRecommendation,
    ) -> MailResult:
        subject = (
            "Safety strategic recommendation "
            f"{recommendation.period_start} to {recommendation.period_end}"
        )
        text = self._strategic_recommendation_text(recommendation)
        html = self._strategic_recommendation_html(recommendation)

        return await self.send_email(
            subject=subject,
            text=text,
            html=html,
            category="strategic-recommendation",
        )

    def _validate_configuration(self) -> None:
        missing_values = []
        if not self.api_token:
            missing_values.append("MAILTRAP_API_TOKEN")
        if not self.sender_email:
            missing_values.append("MAILTRAP_SENDER_EMAIL")

        if missing_values:
            raise ValueError(f"Missing mail settings: {', '.join(missing_values)}")

    def _build_payload(
        self,
        to_email: str,
        to_name: str | None,
        subject: str,
        text: str,
        html: str | None,
        category: str | None,
    ) -> dict:
        payload = {
            "from": {
                "email": self.sender_email,
                "name": self.sender_name,
            },
            "to": [
                {
                    "email": to_email,
                }
            ],
            "subject": subject,
            "text": text,
        }

        if to_name:
            payload["to"][0]["name"] = to_name
        if html:
            payload["html"] = html
        if category:
            payload["category"] = category

        return payload

    @staticmethod
    def _strategic_recommendation_text(recommendation: StrategicRecommendation) -> str:
        lines = [
            "Safety strategic recommendation",
            f"Period: {recommendation.period_start} to {recommendation.period_end}",
            f"Location: {recommendation.location_filter or 'all'}",
            f"Incidents analyzed: {recommendation.incident_count}",
            "",
            "Executive summary:",
            recommendation.executive_summary,
            "",
            "Recommended actions:",
        ]

        for action in recommendation.recommended_actions:
            lines.extend(
                [
                    f"- {action.priority} | {action.owner_type} | {action.timeframe}",
                    f"  {action.action}",
                    f"  Reason: {action.reason}",
                ]
            )

        if recommendation.strategic_priorities:
            lines.extend(["", "Top priorities:"])
            for priority in recommendation.strategic_priorities[:3]:
                lines.append(
                    f"- #{priority.rank}: {priority.problem} "
                    f"(score {priority.priority_score}, {priority.severity_signal})"
                )

        return "\n".join(lines)

    @staticmethod
    def _strategic_recommendation_html(recommendation: StrategicRecommendation) -> str:
        location = escape(recommendation.location_filter or "all")
        period = f"{escape(recommendation.period_start)} to {escape(recommendation.period_end)}"
        executive_summary = escape(recommendation.executive_summary)
        observed_summary = escape(recommendation.observed_problem_summary)
        bias_note = escape(recommendation.observability_bias_note)
        graph_html = MailService._priority_graph_html(recommendation)
        actions_html = MailService._action_cards_html(recommendation)
        priorities_html = MailService._priority_cards_html(recommendation)

        return f"""
        <!DOCTYPE html>
        <html lang="en">
          <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Safety strategic recommendation</title>
          </head>
          <body style="background-color:#f4f7fb;margin:0;padding:0;-webkit-text-size-adjust:none;text-size-adjust:none;">
            <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#f4f7fb;">
              <tr>
                <td align="center" style="padding:8px;">
                  <table width="700" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:700px;max-width:100%;background-color:#ffffff;border-radius:8px;overflow:hidden;">
                    <tr>
                      <td style="background-color:#e0f2fe;padding:10px 16px;text-align:center;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#0f172a;">
                        Danfoss Safety Intelligence
                      </td>
                    </tr>
                    <tr>
                      <td align="center" style="padding:28px 24px 16px;">
                        <div style="display:inline-block;background-color:#0f172a;color:#ffffff;border-radius:8px;padding:10px 14px;font-family:Arial,Helvetica,sans-serif;font-size:18px;font-weight:700;">
                          DSI
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 48px 20px;text-align:center;font-family:Arial,Helvetica,sans-serif;">
                        <h1 style="margin:0;color:#0f172a;font-size:38px;line-height:1.15;font-weight:700;">
                          Safety strategic<br>recommendation
                        </h1>
                        <p style="margin:16px 0 0;color:#475569;font-size:16px;line-height:1.45;">
                          {executive_summary}
                        </p>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 28px 24px;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">
                          <tr>
                            <td style="padding:16px;font-family:Arial,Helvetica,sans-serif;color:#0f172a;font-size:14px;">
                              <strong>Period:</strong> {period}<br>
                              <strong>Location:</strong> {location}<br>
                              <strong>Incidents analyzed:</strong> {recommendation.incident_count}<br>
                              <strong>AI generated:</strong> {"yes" if recommendation.ai_generated else "no"}
                            </td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:4px 48px 28px;font-family:Arial,Helvetica,sans-serif;">
                        <h2 style="margin:0 0 12px;color:#0f172a;font-size:22px;line-height:1.2;">Risk priority graph</h2>
                        <p style="margin:0 0 16px;color:#64748b;font-size:14px;line-height:1.4;">
                        
                        </p>
                        {graph_html}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 48px 24px;font-family:Arial,Helvetica,sans-serif;">
                        <h2 style="margin:0 0 12px;color:#0f172a;font-size:22px;">Recommended actions</h2>
                        {actions_html}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 48px 24px;font-family:Arial,Helvetica,sans-serif;">
                        <h2 style="margin:0 0 12px;color:#0f172a;font-size:22px;">Top priorities</h2>
                        {priorities_html}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 48px 32px;font-family:Arial,Helvetica,sans-serif;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">
                          <tr>
                            <td style="border-top:1px solid #cbd5e1;padding-top:16px;color:#475569;font-size:14px;line-height:1.45;">
                              <strong style="color:#0f172a;">Observed pattern:</strong> {observed_summary}<br><br>
                              <strong style="color:#0f172a;">Bias note:</strong> {bias_note}
                            </td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="background-color:#0f172a;padding:16px 24px;text-align:center;font-family:Arial,Helvetica,sans-serif;color:#cbd5e1;font-size:12px;">
                        Generated automatically by Danfoss Safety Intelligence.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """.strip()

    @staticmethod
    def _priority_graph_html(recommendation: StrategicRecommendation) -> str:
        priorities = recommendation.strategic_priorities[:EMAIL_GRAPH_PRIORITY_LIMIT]
        if not priorities:
            return (
                '<p style="margin:0;color:#64748b;font-size:14px;">'
                "No priority clusters were available for this period."
                "</p>"
            )

        max_score = max(priority.priority_score for priority in priorities) or 1
        rows = []
        for priority in priorities:
            width = max(8, round((priority.priority_score / max_score) * 100))
            color = MailService._severity_color(priority.severity_signal)
            rows.append(
                f"""
                <tr>
                  <td style="padding:8px 0 4px;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#0f172a;">
                    #{priority.rank} {escape(priority.problem)}
                  </td>
                  <td style="padding:8px 0 4px;text-align:right;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#0f172a;">
                    {priority.priority_score}
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding:0 0 8px;">
                    <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#e2e8f0;border-radius:8px;">
                      <tr>
                        <td width="{width}%" style="background-color:{color};height:12px;border-radius:8px;font-size:1px;line-height:12px;">&nbsp;</td>
                        <td width="{100 - width}%" style="height:12px;font-size:1px;line-height:12px;">&nbsp;</td>
                      </tr>
                    </table>
                  </td>
                </tr>
                """
            )

        return (
            '<table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation">'
            + "".join(rows)
            + "</table>"
        )

    @staticmethod
    def _action_cards_html(recommendation: StrategicRecommendation) -> str:
        if not recommendation.recommended_actions:
            return '<p style="margin:0;color:#64748b;font-size:14px;">No actions were generated.</p>'

        rows = []
        for action in recommendation.recommended_actions[:EMAIL_ACTION_LIMIT]:
            color = MailService._priority_color(action.priority)
            rows.append(
                f"""
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:12px;background-color:#fff7ed;border-left:5px solid {color};border-radius:8px;">
                  <tr>
                    <td style="padding:14px 16px;font-family:Arial,Helvetica,sans-serif;">
                      <div style="font-size:13px;font-weight:700;color:{color};text-transform:uppercase;">
                        {escape(action.priority)} | {escape(action.owner_type)} | {escape(action.timeframe)}
                      </div>
                      <div style="padding-top:6px;font-size:15px;line-height:1.4;color:#0f172a;">
                        {escape(action.action)}
                      </div>
                      <div style="padding-top:6px;font-size:13px;line-height:1.4;color:#64748b;">
                        {escape(action.reason)}
                      </div>
                    </td>
                  </tr>
                </table>
                """
            )
        return "".join(rows)

    @staticmethod
    def _priority_cards_html(recommendation: StrategicRecommendation) -> str:
        if not recommendation.strategic_priorities:
            return '<p style="margin:0;color:#64748b;font-size:14px;">No priority clusters were available.</p>'

        rows = []
        for priority in recommendation.strategic_priorities[:3]:
            color = MailService._severity_color(priority.severity_signal)
            rows.append(
                f"""
                <table width="100%" border="0" cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:12px;border-top:1px solid #cbd5e1;">
                  <tr>
                    <td style="padding:12px 0;font-family:Arial,Helvetica,sans-serif;">
                      <div style="font-size:15px;font-weight:700;color:#0f172a;">
                        #{priority.rank} {escape(priority.problem)}
                      </div>
                      <div style="padding-top:4px;font-size:13px;color:{color};font-weight:700;">
                        {escape(priority.severity_signal)} | score {priority.priority_score}
                      </div>
                      <div style="padding-top:4px;font-size:13px;color:#64748b;line-height:1.4;">
                        {escape(priority.why_it_matters)}
                      </div>
                    </td>
                  </tr>
                </table>
                """
            )
        return "".join(rows)

    @staticmethod
    def _priority_color(priority: str) -> str:
        return PRIORITY_COLORS.get(priority, DEFAULT_PRIORITY_COLOR)

    @staticmethod
    def _severity_color(severity_signal: str) -> str:
        if "Critical" in severity_signal:
            return PRIORITY_COLORS["Critical"]
        if "High" in severity_signal:
            return PRIORITY_COLORS["High"]
        if "Medium" in severity_signal:
            return PRIORITY_COLORS["Medium"]
        return PRIORITY_COLORS["Low"]
