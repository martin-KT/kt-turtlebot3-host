"""Decode KT telemetry messages into JSON-safe dicts for the web UI."""

from __future__ import annotations

import importlib
import time
from typing import Any

BATTERY_STALE_NS = 500_000_000


def _optional_remote_time_ns(remote_time_ns: object | None) -> int | None:
    """kt_lan may omit remote_time_ns on some deliveries."""

    if remote_time_ns is None:
        return None
    return int(remote_time_ns)


def _remote_time_ns_from_channel_item(item: object) -> int | None:
    return _optional_remote_time_ns(getattr(item, "remote_time_ns", None))


def supply_status_to_string(status: object) -> str:
    """Map interoception SupplyStatus enum to a readable label."""

    name = getattr(status, "name", None)
    if name is None:
        try:
            from kt.messages.interoception_sample.SupplyStatus import SupplyStatus

            name = SupplyStatus(int(status)).name
        except Exception:
            return str(status)
    return str(name).replace("_", " ")


def _decode_lan_sample(sample: object, *, module: str, typename: str) -> object:
    """Decode kt_lan views the same way as lidar (encoded → from_bytes)."""

    try:
        mod = importlib.import_module(f"kt.messages.{module}")
        cls = getattr(mod, typename)
        if isinstance(sample, cls):
            return sample
        encoded = getattr(sample, "encoded", None)
        if encoded is None:
            return sample
        raw = encoded() if callable(encoded) else encoded
        return cls.from_bytes(raw)
    except Exception:
        return sample


def _vector3_dict(vec: object | None) -> dict[str, float] | None:
    if vec is None:
        return None
    return {
        "x": float(getattr(vec, "x", 0.0) or 0.0),
        "y": float(getattr(vec, "y", 0.0) or 0.0),
        "z": float(getattr(vec, "z", 0.0) or 0.0),
    }


def decode_exteroception_lan_sample(sample: object) -> object:
    """Decode a kt_lan ExteroceptionSample view to a message object."""

    sample = _decode_lan_sample(
        sample,
        module="exteroception_sample",
        typename="ExteroceptionSample",
    )
    imus = getattr(sample, "imu", None) or []
    lidars = getattr(sample, "lidar", None) or []
    compass = getattr(sample, "compass", None)
    if not imus and not lidars and compass is None:
        return sample
    try:
        from kt.messages.exteroception_sample import ExteroceptionSample

        kwargs: dict[str, object] = {}
        if imus:
            kwargs["imu"] = list(imus)
        if lidars:
            kwargs["lidar"] = list(lidars)
        if compass is not None:
            kwargs["compass"] = compass
        return ExteroceptionSample.create(**kwargs)
    except Exception:
        return sample


def decode_imu_from_exteroception(sample: object) -> dict[str, object] | None:
    """Take IMU from ExteroceptionSample.imu[0] when present."""

    sample = decode_exteroception_lan_sample(sample)
    imus = getattr(sample, "imu", None) or []
    if len(imus) == 0:
        return None
    imu = imus[0]
    acc = _vector3_dict(getattr(imu, "acc", None))
    gyro = _vector3_dict(getattr(imu, "gyro", None))
    has_acc = bool(getattr(imu, "has_acc", False))
    has_gyro = bool(getattr(imu, "has_gyro", False))
    # OpenCR often leaves flags false while vectors are populated (console path reads raw).
    if acc is not None:
        has_acc = True
    if gyro is not None:
        has_gyro = True
    return {
        "source": str(getattr(imu, "source", "") or ""),
        "acc": acc or {"x": 0.0, "y": 0.0, "z": 0.0},
        "gyro": gyro or {"x": 0.0, "y": 0.0, "z": 0.0},
        "has_acc": has_acc,
        "has_gyro": has_gyro,
    }


def _battery_from_interoception(sample: object) -> object | None:
    battery = getattr(sample, "battery", None)
    if battery is not None:
        return battery
    batteries = getattr(sample, "batteries", None) or []
    if len(batteries) == 0:
        return None
    return batteries[0]


def decode_battery_from_interoception(sample: object) -> dict[str, object] | None:
    """Extract the primary battery reading from an interoception sample."""

    sample = _decode_lan_sample(
        sample,
        module="interoception_sample",
        typename="InteroceptionSample",
    )
    battery = _battery_from_interoception(sample)
    if battery is None:
        return None
    status = getattr(battery, "supply_status", None)
    out: dict[str, object] = {
        "percentage": float(getattr(battery, "percentage", 0.0) or 0.0),
        "voltage": float(getattr(battery, "voltage", 0.0) or 0.0),
        "present": bool(getattr(battery, "present", False)),
    }
    current = getattr(battery, "current", None)
    if current is not None:
        out["current"] = float(current)
    if status is not None:
        out["supply_status"] = supply_status_to_string(status)
    return out


def decode_joints_from_proprioception(
    sample: object,
    *,
    wheel_joint_name_substrings: list[str],
) -> list[dict[str, object]]:
    """Filter raw_joints to wheel-related names (substring match)."""

    sample = _decode_lan_sample(
        sample,
        module="proprioception_sample",
        typename="ProprioceptionSample",
    )
    joints = getattr(sample, "raw_joints", None) or []
    needles = [s.lower() for s in wheel_joint_name_substrings if s]
    rows: list[dict[str, object]] = []
    for joint in joints:
        name = str(getattr(joint, "name", "") or "")
        if needles and not any(n in name.lower() for n in needles):
            continue
        row: dict[str, object] = {
            "name": name,
            "velocity": float(getattr(joint, "velocity", 0.0) or 0.0),
        }
        position = getattr(joint, "position", None)
        if position is not None:
            row["position"] = float(position)
        rows.append(row)
    if not rows and joints and needles:
        for joint in joints:
            name = str(getattr(joint, "name", "") or "")
            row = {
                "name": name,
                "velocity": float(getattr(joint, "velocity", 0.0) or 0.0),
            }
            position = getattr(joint, "position", None)
            if position is not None:
                row["position"] = float(position)
            rows.append(row)
    return rows


def _json_safe_element_value(element: object) -> object:
    payload = getattr(element, "payload", None)
    if payload is None:
        return None
    try:
        raw = bytes(payload)
    except Exception:
        return str(payload)
    if len(raw) == 1:
        return raw[0]
    if len(raw) == 0:
        return None
    return [int(b) for b in raw]


def decode_sensor_state(element_array: object) -> dict[str, object]:
    """Phase-1 ElementArray → JSON-safe dict with raw elements."""

    element_array = _decode_lan_sample(
        element_array,
        module="element_array",
        typename="ElementArray",
    )
    elements = getattr(element_array, "elements", None) or []
    decoded: list[object] = []
    for index in range(len(elements)):
        item = elements[index]
        if item is None:
            decoded.append(None)
        else:
            decoded.append(_json_safe_element_value(item))
    return {
        "count": len(decoded),
        "elements": decoded,
        "note": "raw until mapped",
    }


class TelemetryAccumulator:
    """Latest telemetry snapshots and remote times from drained channel batches."""

    def __init__(self, *, wheel_joint_name_substrings: list[str]) -> None:
        self._wheel_filter = list(wheel_joint_name_substrings)
        self._remote_time_ns: dict[str, int | None] = {
            "imu": None,
            "battery": None,
            "joints": None,
            "sensor_state": None,
        }
        self._imu: dict[str, object] | None = None
        self._battery: dict[str, object] | None = None
        self._joints: list[dict[str, object]] | None = None
        self._sensor_state: dict[str, object] | None = None
        self._battery_last_host_ns: int | None = None

    def apply_imu(
        self,
        decoded: dict[str, object],
        *,
        channel_item: object | None = None,
    ) -> None:
        self._imu = dict(decoded)
        if channel_item is not None:
            self._remote_time_ns["imu"] = _remote_time_ns_from_channel_item(channel_item)

    def ingest_imu_batch(self, batch: tuple[object, ...]) -> None:
        if not batch:
            return
        last = batch[-1]
        decoded = decode_imu_from_exteroception(getattr(last, "value", last))
        if decoded is not None:
            self.apply_imu(decoded, channel_item=last)

    def ingest_battery_batch(self, batch: tuple[object, ...]) -> None:
        if not batch:
            return
        last = batch[-1]
        decoded = decode_battery_from_interoception(getattr(last, "value", last))
        if decoded is not None:
            self._battery = decoded
            self._remote_time_ns["battery"] = _remote_time_ns_from_channel_item(last)
            self._battery_last_host_ns = time.time_ns()

    def ingest_joints_batch(self, batch: tuple[object, ...]) -> None:
        if not batch:
            return
        last = batch[-1]
        self._joints = decode_joints_from_proprioception(
            getattr(last, "value", last),
            wheel_joint_name_substrings=self._wheel_filter,
        )
        self._remote_time_ns["joints"] = _remote_time_ns_from_channel_item(last)

    def ingest_sensor_state_batch(self, batch: tuple[object, ...]) -> None:
        if not batch:
            return
        last = batch[-1]
        self._sensor_state = decode_sensor_state(getattr(last, "value", last))
        self._remote_time_ns["sensor_state"] = _remote_time_ns_from_channel_item(last)

    def snapshot(self) -> dict[str, object]:
        host_ns = time.time_ns()
        stale: dict[str, bool] = {}
        if self._battery_last_host_ns is None:
            stale["battery"] = True
        else:
            stale["battery"] = (host_ns - self._battery_last_host_ns) > BATTERY_STALE_NS

        telemetry: dict[str, object] = {
            "host_unix_ns": host_ns,
            "remote_time_ns": dict(self._remote_time_ns),
            "stale": stale,
        }
        if self._imu is not None:
            telemetry["imu"] = self._imu
        if self._battery is not None:
            telemetry["battery"] = self._battery
        if self._joints is not None:
            telemetry["joints"] = self._joints
        if self._sensor_state is not None:
            telemetry["sensor_state"] = self._sensor_state
        return telemetry


def wheel_joint_filter_from_settings(settings: dict[str, Any]) -> list[str]:
    raw = settings.get("wheel_joint_name_substrings", ["wheel"])
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return ["wheel"]
