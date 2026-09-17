import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict

import aiohttp
import websockets
from dotenv import load_dotenv

# Load .env if present (e.g., for BASE_URL, TOKEN)
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("TOKEN", "valid-token")  # In prod replace with a real JWT from /token

DEVICE_ID = str(uuid.uuid4())

async def send_event(session: aiohttp.ClientSession, event_type: str, payload: Dict[str, Any]):
    """POST an event to the backend.
    Returns the raw response text for debugging.
    """
    url = f"{BASE_URL}/events"
    data = {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "type": event_type,
        "payload": payload,
    }
    async with session.post(url, json=data, headers={"Authorization": f"Bearer {TOKEN}"}) as resp:
        text = await resp.text()
        return text

async def ws_listener():
    """Maintain a persistent WebSocket connection for push commands.
    The server sends a ping every ~30 seconds; we answer with a pong.
    """
    ws_url = f"ws://{BASE_URL.replace('http://', '').replace('https://', '')}/ws/{DEVICE_ID}"
    async with websockets.connect(ws_url, extra_headers={"Authorization": f"Bearer {TOKEN}"}) as ws:
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await ws.send("pong")
                # Future: handle other command types here.
            except websockets.ConnectionClosed:
                print("WebSocket closed – reconnecting in 5 s")
                await asyncio.sleep(5)
                return await ws_listener()

async def main_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            resp = await send_event(session, "accelerometer", {"x": 0.0, "y": 0.0, "z": 1.0})
            print("Event response:", resp)
            await asyncio.sleep(5)

async def main():
    await asyncio.gather(ws_listener(), main_loop())

if __name__ == "__main__":
    asyncio.run(main())
