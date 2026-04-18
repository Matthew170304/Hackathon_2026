# Hackathon_2026

FastAPI backend MVP for the Danfoss AI Safety Intelligence API.

## Local Setup

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

Run tests:

```bash
pytest
```

## Current Status

Completed setup:

- FastAPI app skeleton
- health endpoint
- environment config loading
- dependency file
- pytest smoke test

