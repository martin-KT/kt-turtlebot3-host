"""Background HTTP + WebSocket server for the lidar canvas UI."""

from __future__ import annotations

import asyncio
import json
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from .camera_view import camera_jpeg_message

_STATIC_DIR = Path(__file__).resolve().parent / "static"


class WebVizService:
    """Thread-safe bridge from the KT step loop to browser clients."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self._settings = dict(settings)
        self._lock = threading.Lock()
        self._scan_fields: dict[str, object] = {}
        self._telemetry: dict[str, object] | None = None
        self._latest: dict[str, object] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._clients: set[Any] = set()
        self._server: Any = None
        hz = float(self._settings.get("telemetry_push_hz", 20.0) or 20.0)
        self._telemetry_min_interval_ns = int(1_000_000_000 / hz) if hz > 0 else 0
        self._last_telemetry_broadcast_ns = 0
        self._cmd_linear_x = 0.0
        self._cmd_angular_z = 0.0
        self._last_camera: dict[str, object] | None = None

    @property
    def settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_server, name="web-viz", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10.0):
            raise RuntimeError("web viz server did not become ready")

        if self._settings.get("open_browser"):
            host = str(self._settings["http_bind_host"])
            port = int(self._settings["http_port"])
            if host in ("0.0.0.0", "::"):
                host = "127.0.0.1"
            webbrowser.open(f"http://{host}:{port}/")

    def stop(self) -> None:
        self._stop.set()
        loop = self._loop
        server = self._server
        if loop is not None and server is not None:

            def _request_exit() -> None:
                server.should_exit = True

            loop.call_soon_threadsafe(_request_exit)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._thread = None
        self._loop = None
        self._server = None

    def _clamp_cmd_vel(self, linear_x: float, angular_z: float) -> tuple[float, float]:
        max_lin = float(self._settings.get("max_linear_m_s", 0.22))
        max_ang = float(self._settings.get("max_angular_rad_s", 2.84))
        lin = max(-max_lin, min(max_lin, float(linear_x)))
        ang = max(-max_ang, min(max_ang, float(angular_z)))
        return lin, ang

    def set_cmd_vel(self, linear_x: float, angular_z: float) -> tuple[float, float]:
        lin, ang = self._clamp_cmd_vel(linear_x, angular_z)
        with self._lock:
            self._cmd_linear_x = lin
            self._cmd_angular_z = ang
        return lin, ang

    def cmd_vel(self) -> tuple[float, float]:
        with self._lock:
            return self._cmd_linear_x, self._cmd_angular_z

    def apply_cmd_vel_message(self, message: object) -> tuple[float, float] | None:
        if not isinstance(message, dict):
            return None
        linear_x = message.get("linear_x", 0.0)
        angular_z = message.get("angular_z", 0.0)
        try:
            return self.set_cmd_vel(float(linear_x), float(angular_z))
        except (TypeError, ValueError):
            return None

    def push_scan(self, payload: dict[str, object]) -> None:
        """Update scan fields and broadcast immediately (new lidar revolution)."""

        self.push_state(payload, from_scan=True)

    def push_camera(self, *, frame_number: int, jpeg: bytes) -> None:
        """Send one JPEG on its own WebSocket message. Does not change the scan payload."""

        message = camera_jpeg_message(frame_number=frame_number, jpeg=jpeg)
        with self._lock:
            self._last_camera = dict(message)
        loop = self._loop
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(message), loop)

    def latest_camera(self) -> dict[str, object] | None:
        with self._lock:
            if self._last_camera is None:
                return None
            return dict(self._last_camera)

    def push_telemetry(self, telemetry: dict[str, object]) -> None:
        """Update telemetry and broadcast subject to telemetry_push_hz throttle."""

        with self._lock:
            self._telemetry = dict(telemetry)
            payload = self._merged_locked()
            self._latest = payload
        self._maybe_broadcast(payload, from_scan=False)

    def push_state(self, payload: dict[str, object], *, from_scan: bool = False) -> None:
        with self._lock:
            if "telemetry" in payload:
                self._telemetry = dict(payload["telemetry"])  # type: ignore[arg-type]
            for key, value in payload.items():
                if key != "telemetry":
                    self._scan_fields[key] = value
            merged = self._merged_locked()
            self._latest = merged
        self._maybe_broadcast(merged, from_scan=from_scan)

    def _merged_locked(self) -> dict[str, object]:
        merged: dict[str, object] = dict(self._scan_fields)
        if self._telemetry is not None:
            merged["telemetry"] = dict(self._telemetry)
        return merged

    def _maybe_broadcast(self, payload: dict[str, object], *, from_scan: bool) -> None:
        del from_scan
        now = time.time_ns()
        with self._lock:
            self._last_telemetry_broadcast_ns = now
        loop = self._loop
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), loop)

    def latest_scan(self) -> dict[str, object] | None:
        with self._lock:
            if self._latest is None:
                return None
            return dict(self._latest)

    async def _broadcast(self, payload: dict[str, object]) -> None:
        dead: list[Any] = []
        try:
            body = json.dumps(payload)
        except (TypeError, ValueError):
            body = json.dumps(payload, default=str)
        for ws in list(self._clients):
            try:
                await ws.send_text(body)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    async def _ws_handler(self, websocket: Any) -> None:
        from starlette.websockets import WebSocketDisconnect

        await websocket.accept()
        self._clients.add(websocket)
        latest = self.latest_scan()
        if latest is not None:
            await websocket.send_text(json.dumps(latest))
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                self.apply_cmd_vel_message(msg)
        except WebSocketDisconnect:
            pass
        finally:
            self._clients.discard(websocket)

    def _build_app(self) -> Any:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import FileResponse, JSONResponse
        from starlette.routing import Route, WebSocketRoute

        service = self

        async def index(_request: object) -> FileResponse:
            return FileResponse(_STATIC_DIR / "index.html")

        async def viz_js(_request: object) -> FileResponse:
            return FileResponse(_STATIC_DIR / "viz.js", media_type="application/javascript")

        async def config_json(_request: object) -> JSONResponse:
            return JSONResponse(
                {
                    "base_frame": service._settings["base_frame"],
                    "max_range_m": service._settings["max_range_m"],
                    "robot_icon_radius_m": service._settings["robot_icon_radius_m"],
                    "sidebar_width_percent": service._settings.get("sidebar_width_percent", 25.0),
                    "max_linear_m_s": service._settings.get("max_linear_m_s", 0.22),
                    "max_angular_rad_s": service._settings.get("max_angular_rad_s", 2.84),
                    "imu_plot_window_s": service._settings.get("imu_plot_window_s", 5.0),
                    "telemetry_push_hz": service._settings.get("telemetry_push_hz", 20.0),
                    "wheel_joint_name_substrings": service._settings.get(
                        "wheel_joint_name_substrings",
                        ["wheel"],
                    ),
                }
            )

        async def scan_json(_request: object) -> JSONResponse:
            latest = service.latest_scan()
            if latest is None:
                return JSONResponse(
                    {
                        "points": [],
                        "scan_unix_ns": 0,
                        "frame": service._settings["base_frame"],
                    }
                )
            return JSONResponse(latest)

        async def cmd_vel_json(request: Request) -> JSONResponse:
            try:
                body = await request.json()
            except json.JSONDecodeError:
                return JSONResponse({"error": "invalid json"}, status_code=400)
            applied = service.apply_cmd_vel_message(body)
            if applied is None:
                return JSONResponse({"error": "expected linear_x and angular_z numbers"}, status_code=400)
            lin, ang = applied
            return JSONResponse({"ok": True, "linear_x": lin, "angular_z": ang})

        routes = [
            Route("/", index),
            Route("/viz.js", viz_js),
            Route("/config.json", config_json),
            Route("/scan.json", scan_json),
            Route("/cmd_vel.json", cmd_vel_json, methods=["POST"]),
            WebSocketRoute("/ws", service._ws_handler),
        ]
        return Starlette(routes=routes)

    def _run_server(self) -> None:
        import uvicorn

        app = self._build_app()
        host = str(self._settings["http_bind_host"])
        port = int(self._settings["http_port"])
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="warning",
            ws="auto",
        )
        server = uvicorn.Server(config)
        self._server = server

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_until_complete(server.serve())
        loop.close()
