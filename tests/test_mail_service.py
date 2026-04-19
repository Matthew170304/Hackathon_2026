import json

import httpx
import pytest

from app.services.mail import MailService
from app.schemas.analytics_schemas import (
    StrategicAction,
    StrategicDataQuality,
    StrategicPeriod,
    StrategicPriority,
    StrategicRecommendation,
)


@pytest.mark.asyncio
async def test_send_email_posts_mailtrap_payload():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, text="accepted")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = MailService(
            api_token="token-123",
            sender_email="safety@example.com",
            sender_name="Safety Bot",
            api_url="https://mailtrap.test/api/send",
            http_client=client,
        )

        result = await service.send_email(
            subject="Safety update",
            text="Please review the incident.",
            to_email="worker@example.com",
            to_name="Worker",
            html="<p>Please review the incident.</p>",
            category="safety",
        )

    assert result.sent is True
    assert result.status_code == 202

    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://mailtrap.test/api/send"
    assert request.headers["Authorization"] == "Bearer token-123"

    payload = json.loads(request.content)
    assert payload == {
        "from": {
            "email": "safety@example.com",
            "name": "Safety Bot",
        },
        "to": [
            {
                "email": "worker@example.com",
                "name": "Worker",
            }
        ],
        "subject": "Safety update",
        "text": "Please review the incident.",
        "html": "<p>Please review the incident.</p>",
        "category": "safety",
    }


@pytest.mark.asyncio
async def test_send_email_returns_unsent_for_failed_mailtrap_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = MailService(
            api_token="bad-token",
            sender_email="safety@example.com",
            http_client=client,
        )

        result = await service.send_email(
            subject="Safety update",
            text="Please review the incident.",
            to_email="worker@example.com",
        )

    assert result.sent is False
    assert result.status_code == 401
    assert result.response_text == "unauthorized"


@pytest.mark.asyncio
async def test_send_email_requires_mailtrap_settings():
    service = MailService(api_token="", sender_email="")

    with pytest.raises(ValueError, match="MAILTRAP_API_TOKEN, MAILTRAP_SENDER_EMAIL"):
        await service.send_email(
            subject="Safety update",
            text="Please review the incident.",
            to_email="worker@example.com",
        )


@pytest.mark.asyncio
async def test_send_email_uses_hardcoded_default_recipient():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, text="accepted")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = MailService(
            api_token="token-123",
            sender_email="safety@example.com",
            http_client=client,
        )

        result = await service.send_email(
            subject="Safety update",
            text="Please review the incident.",
        )

    assert result.sent is True

    payload = json.loads(requests[0].content)
    assert payload["to"] == [{"email": "ilavskymatus@gmail.com"}]


@pytest.mark.asyncio
async def test_send_strategic_recommendation_uses_default_recipient():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, text="accepted")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = MailService(
            api_token="token-123",
            sender_email="safety@example.com",
            http_client=client,
        )

        result = await service.send_strategic_recommendation(_strategic_recommendation())

    assert result.sent is True

    payload = json.loads(requests[0].content)
    assert payload["to"] == [{"email": "ilavskymatus@gmail.com"}]
    assert payload["category"] == "strategic-recommendation"
    assert "Safety strategic recommendation" in payload["subject"]
    assert "Executive summary" in payload["text"]
    assert "Improve guarding" in payload["html"]


def _strategic_recommendation() -> StrategicRecommendation:
    action = StrategicAction(
        priority="High",
        owner_type="Maintenance",
        timeframe="30 days",
        action="Improve guarding.",
        reason="Repeated high-risk machine reports.",
        expected_impact="Lower machine exposure.",
    )
    return StrategicRecommendation(
        period_start="2025-01-01",
        period_end="2025-12-31",
        location_filter=None,
        incident_count=3,
        ai_generated=False,
        methodology="Weighted evidence model.",
        period=StrategicPeriod(
            start="2025-01-01",
            end="2025-12-31",
            location_filter=None,
        ),
        data_quality=StrategicDataQuality(
            incident_count=3,
            missing_severity_rate=0.0,
            missing_recurrence_rate=0.0,
            unknown_hazard_rate=0.0,
            unknown_cause_rate=0.0,
            needs_review_rate=0.0,
            average_confidence=0.8,
            reporting_bias_assessment="Moderate uncertainty.",
            data_limitations=[],
        ),
        strategic_priorities=[
            StrategicPriority(
                rank=1,
                problem="Machine guarding risk",
                cluster_key="Site | Activity | Mechanical | Procedures",
                priority_score=88.0,
                confidence=0.8,
                observed_frequency=3,
                average_risk_score=50.0,
                max_risk_score=125,
                critical_count=1,
                severity_signal="Critical potential present",
                recurrence_signal="Recurring within months",
                observability="medium",
                underreporting_likelihood="Medium",
                why_it_matters="High severity potential.",
                evidence_case_ids=["case-1"],
                recommended_actions=[action],
            )
        ],
        executive_summary="Executive summary text.",
        observed_problem_summary="Observed hazard pattern: Mechanical: 3",
        observability_bias_note="Low counts can hide risk.",
        most_observed_problems=[],
        hidden_risk_hypotheses=[],
        recommended_actions=[action],
    )
