# All‑In‑One Personal Bot

A **self‑hosted** service that connects to any device (mobile, desktop, wearables), ingests sensor data, learns a user’s routines, and provides periodic updates, reminders, and context‑aware actions. The prototype consists of:

* **FastAPI backend** – handles authentication, event ingestion, and a WebSocket channel for push commands.
* **Python client** – a lightweight example that streams dummy accelerometer events and maintains a WebSocket connection.
* **Docker support** – build and run the backend in a container.
* **CI pipeline** – GitHub Actions linting and basic tests (future ready).

The repository is organized for commercial use: a permissive MIT license, a Dockerfile, a `docker‑compose.yml` for local development, and a clear README.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Running with Docker](#running-with-docker)
- [API Reference](#api-reference)
- [Customization & Extensibility](#customization--extensibility)
- [Testing & CI](#testing--ci)
- [Security Considerations](#security-considerations)
- [License](#license)
- [Contributing](#contributing)

---

## Features

- **Device‑agnostic remote connection** – devices authenticate with JWTs and open a persistent WebSocket.
- **Event ingestion** – `/events` receives arbitrary JSON payloads (sensor data, app usage, etc.).
- **Push notifications** – the backend can send commands, reminders, or UI overlay instructions via WebSocket.
- **Extensible authentication** – demo token endpoint provided; replace with OAuth2, SSO, or custom device‑pairing flow.
- **CORS enabled** – safe for front‑end integrations.
- **Docker‑first** – container builds in seconds, ready for cloud or on‑prem deployments.
- **CI ready** – linting with `ruff`/`flake8` and type‑checking with `mypy` are wired in GitHub Actions.

---

## Architecture Overview

```mermaid
graph TD;
    Client[Device Client] -->|WebSocket / HTTPS| Backend[FastAPI Backend];
    Backend -->|Store / Process| DB[(PostgreSQL / Vector Store)];
    Backend -->|Calls| LLM[LLM / Learning Engine];
    Client -->|Sensor APIs| Sensors[OS / Wearable Sensors];
    Backend -->|Integrations| Ext[External Services (Google, Outlook, Slack)];
```

The diagram shows the main data flow:

* Devices send telemetry to the **backend** via HTTPS POSTs and maintain a **WebSocket** for real‑time commands.
* The backend can persist events in a **database**, forward them to a **learning engine** (e.g., OpenAI fine‑tuning) and call third‑party APIs (Google Calendar, Slack, etc.).
* The **mirror‑mask UI** lives on the device side and reacts to messages received over the WebSocket.

---

## Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/all-in-one-bot.git
   cd all-in-one-bot
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend**
   ```bash
   uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
   ```
   The server will be reachable at `http://localhost:8000`.

5. **Open a second terminal** and run the example client:
   ```bash
   source .venv/bin/activate
   python client/example_client.py
   ```
   You should see the client posting dummy events every 5 seconds and a ping/pong exchange over the WebSocket.

6. **Verify**
   ```bash
   curl http://localhost:8000/ping
   # → {"msg":"pong"}
   ```

---

## Running with Docker

The repository ships with a Dockerfile that builds the backend and a `docker‑compose.yml` for quick orchestration.

```bash
# Build and start the backend (exposes port 8000)
 docker compose up --build -d
```

You can now reach the API at `http://localhost:8000`. The client works unchanged because it still points to `http://localhost:8000`.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/token` | Demo endpoint that returns a JWT. Replace with a real auth flow in production. |
| `GET`  | `/ping` | Health check – returns `{ "msg": "pong" }`. |
| `POST` | `/events` | Ingest a telemetry event. Payload matches the `Event` model (device_id, timestamp, type, payload). |
| `WS`   | `/ws/{device_id}` | Persistent channel for push commands. Server sends a `ping` every 30 s; client should reply with any text (e.g., `pong`). |

All routes are protected by JWT authentication (except `/token` in the demo).

---

## Customization & Extensibility

### Adding a Database
Replace the `# TODO: Persist the event.` comment in `backend/api.py` with an async call to your data layer (e.g., SQLAlchemy + PostgreSQL). A typical pattern:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from .models import EventModel

async def ingest_event(event: Event, db: AsyncSession = Depends(get_db)):
    db_event = EventModel(**event.dict())
    db.add(db_event)
    await db.commit()
    return EventResponse()
```

### Real Device Authentication
Implement a `/pair` endpoint that returns a short‑lived pairing code. The device scans a QR code, posts the code, and receives a signed JWT.

### Learning Engine
Push events into a message queue (RabbitMQ, Kafka, or Redis Streams) and have a separate worker poll the queue, compute habit patterns, and write suggestions back to a dedicated `/commands` endpoint that the client can fetch via WebSocket.

---

## Testing & CI

The repository includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every push:

* **Linting** – `ruff` (fast Python linter) ensures code style.
* **Type‑checking** – `mypy` catches type‑related bugs.
* **Unit tests** – placeholder folder `tests/` (add your own tests).

You can trigger the workflow locally with:
```bash
act -j lint   # if you have the `act` CLI installed
```

---

## Security Considerations

* **Secret management** – never commit real secrets. Use a `.env` file (ignored via `.gitignore`) and a secret manager in production (AWS Secrets Manager, Vault, etc.).
* **CORS** – tighten `allowed_origins` to your domain(s) before exposing the service publicly.
* **Rate limiting** – add a middleware (e.g., `slowapi`) to protect the token endpoint.
* **Input validation** – the generic `payload: Dict[str, Any]` accepts any JSON. For a production service you’ll want per‑event schemas or JSON‑Schema validation.
* **HTTPS** – run behind a TLS terminator (NGINX, Traefik, Cloud‑LB) in production.

---

## License

MIT License – see the `LICENSE` file for details.

---

## Contributing

Contributions are welcome! Fork the repo, create a feature branch, and open a PR. Please ensure the CI pipeline passes before submitting.

---

**Happy hacking!**
