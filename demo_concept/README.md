# AppBank Voice Pipeline

This repo now implements a minimal speech-first demo flow:

Mic Input
-> Amazon Transcribe streaming STT
-> Amazon Nova intent detection
-> Action router
-> Mock FastAPI action endpoint
-> Console / JSON response

## Backend

The backend lives in `backend/appbank_digital_twin/main.py` and serves both the API and the demo frontend.

Available endpoints:

- `GET /` demo UI for microphone capture and live visualization
- `GET /v1/health` service health check
- `WS /v1/pipeline/ws` voice pipeline websocket
- `POST /v1/mock-actions/execute` mock action endpoint

## Environment

Create `backend/.env` from `backend/.env.example`.

Required variables:

- `AWS_REGION`
- `AWS_TRANSCRIBE_LANGUAGE_CODE`
- `AWS_TRANSCRIBE_SAMPLE_RATE_HZ`
- `AWS_NOVA_MODEL_ID`

AWS credentials must be available through the standard AWS SDK credential chain.

## Run

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m uvicorn appbank_digital_twin.main:app --reload
```

Then open `http://127.0.0.1:8000` and start the microphone session.
