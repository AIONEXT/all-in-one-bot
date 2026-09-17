import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, BaseSettings
from jose import JWTError, jwt

# ---------------------------------------------------------------------------
# Settings – loaded from a .env file in production. Adjust before deploying.
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    access_token_expire_minutes: int = 60
    allowed_origins: List[str] = ["*"]  # Replace with your domain list in prod.

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# ---------------------------------------------------------------------------
# JWT helpers – use HS256. In a real service you would have a user store.
# ---------------------------------------------------------------------------
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        device_id: Optional[str] = payload.get("device_id")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id, "device_id": device_id}
    except JWTError:
        raise credentials_exception

# ---------------------------------------------------------------------------
# FastAPI app configuration
# ---------------------------------------------------------------------------
app = FastAPI(title="All‑In‑One Personal Bot Backend", version="1.0.0")

# CORS – tighten allowed_origins for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple logger – in prod configure a proper logging config.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot-backend")

# ---------------------------------------------------------------------------
# Security – OAuth2 bearer token (placeholder /token endpoint).
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    # Development shortcut – accept a hard‑coded token.
    if token == "valid-token":
        return {"user_id": "dev_user", "device_id": "dev_device"}
    return verify_token(token)

# ---------------------------------------------------------------------------
# Pydantic models for API payloads
# ---------------------------------------------------------------------------
class Event(BaseModel):
    device_id: str
    timestamp: datetime
    type: str
    payload: Dict[str, Any]

class EventResponse(BaseModel):
    status: str = "accepted"

class PingResponse(BaseModel):
    msg: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/events", response_model=EventResponse)
async def ingest_event(event: Event, user: dict = Depends(get_current_user)):
    """Receive a telemetry event from a device.
    In production store the event (e.g., Postgres, ClickHouse) and forward it
    to an async processing pipeline.
    """
    logger.info(
        "Event from %s (user=%s) – %s: %s",
        event.device_id,
        user.get("user_id"),
        event.type,
        event.payload,
    )
    # TODO: Persist the event.
    return EventResponse()

@app.get("/ping", response_model=PingResponse)
async def ping():
    return PingResponse(msg="pong")

# ---------------------------------------------------------------------------
# Demo token endpoint – replace with real auth in production.
# ---------------------------------------------------------------------------
@app.post("/token", response_model=TokenResponse)
async def get_token():
    """Issue a demo JWT for quick local testing.
    In a real product you would verify a password, an OAuth provider, or a
    device‑pairing secret before issuing a token.
    """
    demo_user = "demo_user"
    demo_device = "demo_device"
    access_token = create_access_token({"sub": demo_user, "device_id": demo_device})
    return TokenResponse(access_token=access_token)

# ---------------------------------------------------------------------------
# WebSocket – push notifications or commands to a connected device.
# ---------------------------------------------------------------------------
@app.websocket("/ws/{device_id}")
async def ws_push(socket: WebSocket, device_id: str):
    await socket.accept()
    logger.info("WebSocket opened for device %s", device_id)
    try:
        while True:
            # Simple keep‑alive ping every 30 seconds.
            await socket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat()})
            # Wait for any client message (e.g., a pong) to keep the connection alive.
            try:
                await socket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception as exc:
        logger.error("WebSocket error for %s: %s", device_id, exc)
    finally:
        await socket.close()
        logger.info("WebSocket closed for device %s", device_id)

# ---------------------------------------------------------------------------
# Entrypoint for `python -m uvicorn backend.api:app`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
