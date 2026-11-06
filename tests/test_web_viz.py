"""HTTP snapshot and WebSocket stay-up smoke (local server thread)."""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request

from kt_turtlebot3_host.web_viz import WebVizService


def _wait_http(url: str, *, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                resp.read(1)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.05)
    raise AssertionError(f"server did not accept HTTP within {timeout_s}s: {last_error}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_scan_json_and_websocket_accepts() -> None:
    port = _free_port()
    service = WebVizService(
        {
            "http_bind_host": "127.0.0.1",
            "http_port": port,
            "open_browser": False,
            "base_frame": "base_link",
            "robot_icon_radius_m": 0.15,
            "max_range_m": 3.5,
            "sidebar_width_percent": 25.0,
            "max_linear_m_s": 0.22,
            "max_angular_rad_s": 2.84,
            "imu_plot_window_s": 5.0,
            "telemetry_push_hz": 20.0,
            "wheel_joint_name_substrings": ["wheel"],
        }
    )
    service.start()
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_http(f"{base}/config.json")
        payload = {
            "scan_unix_ns": 99,
            "frame": "base_link",
            "link": "base_scan",
            "points": [[1.0, 0.0, 50.0], [0.0, 1.5, 0.0]],
        }
        telemetry = {
            "host_unix_ns": 456,
            "remote_time_ns": {"imu": 789, "battery": None, "joints": None, "sensor_state": None},
            "stale": {"battery": True},
            "imu": {
                "source": "imu_link",
                "acc": {"x": 0.0, "y": 0.0, "z": 9.81},
                "gyro": {"x": 0.0, "y": 0.0, "z": 0.01},
                "has_acc": True,
                "has_gyro": True,
            },
        }
        service.push_scan(payload)
        service.push_telemetry(telemetry)

        with urllib.request.urlopen(f"{base}/config.json", timeout=5) as resp:
            cfg = json.loads(resp.read().decode("utf-8"))
        assert cfg["imu_plot_window_s"] == 5.0
        assert cfg["sidebar_width_percent"] == 25.0
        assert cfg["max_linear_m_s"] == 0.22
        assert "wheel_joint_name_substrings" in cfg

        req = urllib.request.Request(
            f"{base}/cmd_vel.json",
            data=json.dumps({"linear_x": 0.1, "angular_z": -0.2}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            cmd_body = json.loads(resp.read().decode("utf-8"))
        assert cmd_body["ok"] is True
        assert cmd_body["linear_x"] == 0.1
        assert cmd_body["angular_z"] == -0.2
        assert service.cmd_vel() == (0.1, -0.2)

        with urllib.request.urlopen(f"{base}/scan.json", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["scan_unix_ns"] == 99
        assert len(body["points"]) == 2
        assert body["telemetry"]["imu"]["acc"]["z"] == 9.81

        import asyncio

        async def _ws_ping() -> None:
            import websockets

            uri = f"ws://127.0.0.1:{port}/ws"
            async with websockets.connect(uri, open_timeout=5) as ws:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                msg = json.loads(raw)
                assert msg["scan_unix_ns"] == 99
                assert len(msg["points"]) == 2

        asyncio.run(_ws_ping())
    finally:
        service.stop()


def main() -> None:
    test_scan_json_and_websocket_accepts()
    print("Web viz tests passed")


if __name__ == "__main__":
    main()
