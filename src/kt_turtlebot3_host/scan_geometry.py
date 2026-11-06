"""Polar lidar beams → Cartesian points in base_link (2D top-down)."""

from __future__ import annotations

import math
from typing import Any


DEFAULT_RANGE_MIN_M = 0.12


def settings_from_config(config: object) -> dict[str, Any]:
    """Merge runtime/package config defaults for the web viz."""

    defaults: dict[str, Any] = {
        "http_bind_host": "127.0.0.1",
        "http_port": 8765,
        "open_browser": True,
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
    if isinstance(config, dict):
        for key in defaults:
            if key in config and config[key] is not None:
                defaults[key] = config[key]
    defaults["http_port"] = int(defaults["http_port"])
    defaults["open_browser"] = bool(defaults["open_browser"])
    defaults["robot_icon_radius_m"] = float(defaults["robot_icon_radius_m"])
    defaults["max_range_m"] = float(defaults["max_range_m"])
    defaults["base_frame"] = str(defaults["base_frame"])
    defaults["http_bind_host"] = str(defaults["http_bind_host"])
    defaults["sidebar_width_percent"] = float(defaults["sidebar_width_percent"])
    defaults["max_linear_m_s"] = float(defaults["max_linear_m_s"])
    defaults["max_angular_rad_s"] = float(defaults["max_angular_rad_s"])
    defaults["imu_plot_window_s"] = float(defaults["imu_plot_window_s"])
    defaults["telemetry_push_hz"] = float(defaults["telemetry_push_hz"])
    raw_wheels = defaults["wheel_joint_name_substrings"]
    if isinstance(raw_wheels, list):
        defaults["wheel_joint_name_substrings"] = [str(item) for item in raw_wheels]
    else:
        defaults["wheel_joint_name_substrings"] = ["wheel"]
    return defaults


def _transform_xy_yaw(transform: object | None) -> tuple[float, float, float]:
    if transform is None:
        return 0.0, 0.0, 0.0
    position = getattr(transform, "position", None)
    euler = getattr(transform, "euler_angles", None)
    tx = float(getattr(position, "x", 0.0) or 0.0) if position is not None else 0.0
    ty = float(getattr(position, "y", 0.0) or 0.0) if position is not None else 0.0
    yaw = float(getattr(euler, "z", 0.0) or 0.0) if euler is not None else 0.0
    return tx, ty, yaw


def _lidar_beams_and_values(lidar: object) -> tuple[int, list[float]]:
    """Match report.format_scan beam/range indexing on decoded Lidar views."""

    shape = [int(item) for item in list(getattr(lidar, "data_shape"))]
    beams = shape[1] if len(shape) >= 2 else 0
    values = list(getattr(lidar, "data"))
    return beams, values


def _valid_range(range_m: float, *, range_min_m: float, range_max_m: float) -> bool:
    if not math.isfinite(range_m) or range_m <= 0.0:
        return False
    if range_m < range_min_m or range_m > range_max_m:
        return False
    return True


def lidar_to_points(
    lidar: object,
    *,
    range_min_m: float = DEFAULT_RANGE_MIN_M,
    range_max_m: float = 3.5,
) -> list[list[float]]:
    """Return [[x, y, intensity], ...] in base_link (metres)."""

    beams, values = _lidar_beams_and_values(lidar)
    if beams <= 0 or len(values) < beams:
        return []
    has_intensity_row = len(values) >= beams * 2

    start = float(getattr(lidar, "horizontal_start_angle", 0.0) or 0.0)
    step = float(getattr(lidar, "horizontal_angular_resolution", 0.0) or 0.0)
    tx, ty, yaw = _transform_xy_yaw(getattr(lidar, "transform", None))
    cos_y = math.cos(yaw)
    sin_y = math.sin(yaw)

    points: list[list[float]] = []
    for index in range(beams):
        range_m = float(values[index])
        intensity = float(values[beams + index]) if has_intensity_row else 0.0
        if not _valid_range(range_m, range_min_m=range_min_m, range_max_m=range_max_m):
            continue
        # LDS-01 beam index increases clockwise from forward; ROS base_link +Y is left.
        angle = start + index * step
        x_s = range_m * math.cos(angle)
        y_s = -range_m * math.sin(angle)
        x_b = cos_y * x_s - sin_y * y_s + tx
        y_b = sin_y * x_s + cos_y * y_s + ty
        points.append([x_b, y_b, intensity])
    return points


def lidar_to_payload(
    lidar: object,
    *,
    base_frame: str,
    range_min_m: float = DEFAULT_RANGE_MIN_M,
    range_max_m: float = 3.5,
) -> dict[str, object]:
    """JSON-serialisable scan for the browser."""

    transform = getattr(lidar, "transform", None)
    link_name = ""
    if transform is not None:
        link_name = str(getattr(transform, "link_name", "") or "")
    return {
        "scan_unix_ns": int(getattr(lidar, "scan_unix_ns", 0) or 0),
        "frame": base_frame,
        "link": link_name,
        "points": lidar_to_points(
            lidar,
            range_min_m=range_min_m,
            range_max_m=range_max_m,
        ),
    }


def publish_scan_if_new(
    sample: object,
    publisher: object | None,
    *,
    base_frame: str,
    range_min_m: float = DEFAULT_RANGE_MIN_M,
    max_range_m: float = 3.5,
) -> bool:
    """Push to the web layer only when lidar[0].new_data_flag is true."""

    if publisher is None:
        return False
    lidars = getattr(sample, "lidar", None) or []
    if not lidars:
        return False
    lidar = lidars[0]
    if not bool(getattr(lidar, "new_data_flag", False)):
        return False
    # Encoded lidar view (same as tests): Construction alone may lack `.data`.
    if not hasattr(lidar, "data") or lidar.data is None:
        try:
            from kt.messages.exteroception_sample import ExteroceptionSample

            if hasattr(sample, "lidar"):
                lidar = ExteroceptionSample.create(lidar=list(lidars)).lidar[0]
        except Exception:
            pass
    payload = lidar_to_payload(
        lidar,
        base_frame=base_frame,
        range_min_m=range_min_m,
        range_max_m=max_range_m,
    )
    push = getattr(publisher, "push_scan", None)
    if push is None:
        return False
    push(payload)
    return True
