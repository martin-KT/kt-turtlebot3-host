"""Decode IMU, battery, joints, and sensor state for the web sidebar."""

from __future__ import annotations

import time

from kt.messages.element_array import Element, ElementArray
from kt.messages.exteroception_sample import ExteroceptionSample, IMU, Vector3
from kt.messages.interoception_sample import Battery, InteroceptionSample, SupplyStatus
from kt.messages.proprioception_sample import Joint, ProprioceptionSample

from kt_turtlebot3_host.telemetry import (
    TelemetryAccumulator,
    decode_battery_from_interoception,
    decode_imu_from_exteroception,
    decode_joints_from_proprioception,
    decode_sensor_state,
    supply_status_to_string,
)


def test_supply_status_readable() -> None:
    assert supply_status_to_string(SupplyStatus.Discharging) == "Discharging"
    assert supply_status_to_string(SupplyStatus.Not_Charging) == "Not Charging"


def test_decode_imu_from_encoded_exteroception_sample() -> None:
    imu = IMU.create(
        source="imu_link",
        acc=Vector3.create(x=1.0, y=2.0, z=3.0),
        gyro=Vector3.create(x=0.1, y=0.2, z=0.3),
        has_acc=True,
        has_gyro=True,
    )
    sample = ExteroceptionSample.create(imu=[imu])
    expected = decode_imu_from_exteroception(sample)
    assert expected is not None
    raw = sample.encoded()

    class _KtLanView:
        def encoded(self) -> object:
            return raw

    decoded = decode_imu_from_exteroception(_KtLanView())
    assert decoded is not None
    assert decoded == expected


def test_decode_imu_sets_has_flags_when_vectors_present() -> None:
    imu = IMU.create(
        source="imu_link",
        acc=Vector3.create(x=0.0, y=0.0, z=9.81),
        gyro=Vector3.create(x=0.01, y=0.0, z=0.0),
        has_acc=False,
        has_gyro=False,
    )
    sample = ExteroceptionSample.create(imu=[imu])
    decoded = decode_imu_from_exteroception(sample)
    assert decoded is not None
    assert decoded["has_acc"] is True
    assert decoded["has_gyro"] is True


def test_decode_imu_from_exteroception_sample() -> None:
    imu = IMU.create(
        source="imu_link",
        acc=Vector3.create(x=0.0, y=0.0, z=9.81),
        gyro=Vector3.create(x=0.01, y=0.02, z=0.03),
        has_acc=True,
        has_gyro=True,
    )
    sample = ExteroceptionSample.create(imu=[imu])
    decoded = decode_imu_from_exteroception(sample)
    assert decoded is not None
    assert decoded["source"] == "imu_link"
    assert abs(decoded["acc"]["z"] - 9.81) < 0.001
    assert abs(decoded["gyro"]["z"] - 0.03) < 0.001
    assert decoded["has_acc"] is True


def test_decode_battery_from_interoception_sample() -> None:
    battery = Battery.create(
        percentage=87.0,
        voltage=12.1,
        current=0.4,
        present=True,
        supply_status=SupplyStatus.Discharging,
    )
    sample = InteroceptionSample.create(batteries=[battery])
    decoded = decode_battery_from_interoception(sample)
    assert decoded is not None
    assert decoded["percentage"] == 87.0
    assert decoded["supply_status"] == "Discharging"
    assert abs(decoded["current"] - 0.4) < 0.001


def test_decode_joints_filters_wheel_names() -> None:
    joints = [
        Joint.create(name="wheel_left_joint", velocity=0.5, position=1.0),
        Joint.create(name="joint_arm", velocity=9.0),
    ]
    sample = ProprioceptionSample.create(raw_joints=joints)
    rows = decode_joints_from_proprioception(
        sample,
        wheel_joint_name_substrings=["wheel"],
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "wheel_left_joint"
    assert rows[0]["velocity"] == 0.5
    assert rows[0]["position"] == 1.0


def test_decode_sensor_state_raw_elements() -> None:
    arr = ElementArray.create(
        elements=[
            Element.create(payload=bytes([0])),
            Element.create(payload=bytes([1])),
        ]
    )
    decoded = decode_sensor_state(arr)
    assert decoded["count"] == 2
    assert decoded["elements"] == [0, 1]
    assert "raw until mapped" in decoded["note"]


def test_accumulator_accepts_none_remote_time_ns() -> None:
    class _Recv:
        def __init__(self, value: object, remote_time_ns: int | None) -> None:
            self.value = value
            self.remote_time_ns = remote_time_ns

    imu = IMU.create(
        source="imu_link",
        acc=Vector3.create(x=0.0, y=0.0, z=1.0),
        gyro=Vector3.create(x=0.0, y=0.0, z=0.0),
        has_acc=True,
        has_gyro=True,
    )
    sample = ExteroceptionSample.create(imu=[imu])
    acc = TelemetryAccumulator(wheel_joint_name_substrings=["wheel"])
    acc.ingest_imu_batch((_Recv(sample, None),))
    snap = acc.snapshot()
    assert snap["remote_time_ns"]["imu"] is None
    assert snap["imu"] is not None


def test_accumulator_marks_stale_battery() -> None:
    acc = TelemetryAccumulator(wheel_joint_name_substrings=["wheel"])
    snap = acc.snapshot()
    assert snap["stale"]["battery"] is True

    class _Recv:
        def __init__(self, value: object, remote_time_ns: int) -> None:
            self.value = value
            self.remote_time_ns = remote_time_ns

    battery = Battery.create(percentage=50.0, voltage=11.0, present=True)
    sample = InteroceptionSample.create(batteries=[battery])
    acc.ingest_battery_batch((_Recv(sample, 100),))
    snap2 = acc.snapshot()
    assert snap2["stale"]["battery"] is False
    assert snap2["battery"]["percentage"] == 50.0

    acc._battery_last_host_ns = time.time_ns() - 600_000_000  # noqa: SLF001
    snap3 = acc.snapshot()
    assert snap3["stale"]["battery"] is True


def main() -> None:
    test_supply_status_readable()
    test_decode_imu_from_encoded_exteroception_sample()
    test_decode_imu_sets_has_flags_when_vectors_present()
    test_decode_imu_from_exteroception_sample()
    test_decode_battery_from_interoception_sample()
    test_decode_joints_filters_wheel_names()
    test_decode_sensor_state_raw_elements()
    test_accumulator_accepts_none_remote_time_ns()
    test_accumulator_marks_stale_battery()
    print("Telemetry tests passed")


if __name__ == "__main__":
    main()
