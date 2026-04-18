# Hackathon_2026

FastAPI backend MVP for the Danfoss AI Safety Intelligence API.

## Local Setup

Create local environment config:

```bash
cp .env.example .env
```

For mock/local demo mode, leave `AI_PROVIDER=mock` and `TRANSLATOR_PROVIDER=mock`.

For real provider mode, set:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your_key
HAZARD_AI_MODEL=gpt-4o-mini

TRANSLATOR_PROVIDER=deepl
DEEPL_API_KEY=your_key
```

Activate the virtual environment:

```bash
cd your_path/Hackathon_2026
source .venv/bin/activate
```

Install dependencies if needed:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

Main MVP endpoints:

```text
POST /incidents
GET /incidents/{incident_id}
POST /uploads/excel
GET /analytics/powerbi/incidents
GET /analytics/risk-clusters?year=2025
GET /analytics/roadmap?year=2025
```

Run tests:

```bash
pytest
```

## Current Status

Completed MVP backend:

- FastAPI app and health endpoint
- incident processing pipeline
- text cleaning, language detection, translation hook
- hybrid hazard and cause classification
- severity and recurrence inference
- Danfoss risk scoring
- recommendation generation
- incident API routes
- Excel upload ingestion
- Power BI-ready analytics endpoint
- risk clusters and prevention roadmap endpoints
- mock fallback mode plus OpenAI/DeepL-ready configuration
