"""
Angle-of-Arrival (AoA) visualization service.

- Listens for UDP packets on 0.0.0.0:5005 containing CSV lines:
      <udp_timestamp>,<azimuth_deg>,<elevation_deg>
- Serves a web UI on http://0.0.0.0:8000 that renders the latest
  azimuth/elevation as a 3D vector in real time (via WebSocket push).
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

UDP_HOST = "0.0.0.0"
UDP_PORT = 5005
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aoa-service")

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Angle of Arrival Service")


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts AoA updates to all of them."""

    def __init__(self) -> None:
        self.active: Set[WebSocket] = set()
        self.latest: dict | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)
        if self.latest is not None:
            await ws.send_text(json.dumps(self.latest))

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, message: dict) -> None:
        self.latest = message
        payload = json.dumps(message)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


class AoAUdpProtocol(asyncio.DatagramProtocol):
    """Receives CSV UDP packets: udp_timestamp,azimuth_deg,elevation_deg"""

    def __init__(self, on_message) -> None:
        self.on_message = on_message
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        log.info("UDP listener bound to %s:%d", UDP_HOST, UDP_PORT)

    def datagram_received(self, data: bytes, addr) -> None:
        try:
            line = data.decode("utf-8", errors="replace").strip()
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                raise ValueError(f"expected at least 3 CSV fields, got {len(parts)}: {line!r}")

            udp_timestamp = float(parts[0])
            azimuth = float(parts[1])
            elevation = float(parts[2])
            # Optional 4th field for beam width (deg); not yet sent by any
            # known source, so the UI falls back to a fixed default when absent.
            beam_width = float(parts[3]) if len(parts) > 3 and parts[3] != "" else None

            message = {
                "udp_timestamp": udp_timestamp,
                "azimuth_deg": azimuth,
                "elevation_deg": elevation,
                "beam_width_deg": beam_width,
                "received_at": time.time(),
                "source": f"{addr[0]}:{addr[1]}",
            }
            asyncio.create_task(self.on_message(message))
        except (ValueError, UnicodeDecodeError) as exc:
            log.warning("Dropping malformed packet from %s: %s", addr, exc)

    def error_received(self, exc: Exception) -> None:
        log.error("UDP error: %s", exc)


@app.on_event("startup")
async def start_udp_listener() -> None:
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(
        lambda: AoAUdpProtocol(manager.broadcast),
        local_addr=(UDP_HOST, UDP_PORT),
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # Client doesn't need to send anything; just keep the connection open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
