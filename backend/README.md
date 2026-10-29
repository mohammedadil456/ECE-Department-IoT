# SmartLab API

FastAPI + SQLite service. Local persistent data is stored at `backend/smartlab.db` by default; Docker Compose mounts a persistent volume at `/data/smartlab.db`.

## Run locally
```python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

## Main routes
- `GET /api/health`
- `GET/POST /api/devices`
- `POST /api/readings` — ingest telemetry JSON
- `GET /api/readings/latest?device_id=smartlab-node-01`
- `GET /api/readings?device_id=smartlab-node-01&limit=100`
- `GET/PUT /api/settings`
- `GET /api/events`

Register another node with `POST /api/devices` before sending its readings. Production deployment should add auth, TLS, restricted CORS, input/device authorization, retention policy, and alert delivery.
