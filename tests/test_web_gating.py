"""Web push is gated on new_data_flag (no live server)."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import kt_process as KT
from kt.messages.exteroception_sample import ExteroceptionSample, Lidar, Transform, Vector3

import kt_turtlebot3_host.process as process_module
from kt_turtlebot3_host.process import Process


class _Received:
    def __init__(self, value: object) -> None:
        self.value = value


class _Feed:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def read_all(self, ctx: object) -> list[_Received]:
        del ctx
        return [_Received(value) for value in self._values]


class _RecordingViz:
    def __init__(self) -> None:
        self.scan_pushes: list[dict[str, object]] = []
        self.telemetry_pushes: list[dict[str, object]] = []

    def push_scan(self, payload: dict[str, object]) -> None:
        self.scan_pushes.append(payload)

    def push_telemetry(self, payload: dict[str, object]) -> None:
        self.telemetry_pushes.append(payload)

    def cmd_vel(self) -> tuple[float, float]:
        return (0.0, 0.0)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _scan(*, scan_unix_ns: int, new_data: bool) -> ExteroceptionSample:
    ranges = [1.0] * 360
    intensities = [0.0] * 360
    lidar = Lidar.create(
        source="base_scan",
        data=ranges + intensities,
        data_shape=[2, 360],
        horizontal_angular_resolution=0.017453292,
        horizontal_start_angle=0.0,
        horizontal_end_angle=6.265732,
        scan_duration=200_000_000,
        time_between_scans=200_000_000,
        transform=Transform.create(
            position=Vector3.create(x=-0.064, y=0.0, z=0.122),
            euler_angles=Vector3.create(x=0.0, y=0.0, z=0.0),
            link_name="base_scan",
            part="base_link",
        ),
        new_data_flag=new_data,
        scan_unix_ns=scan_unix_ns,
        scan_timestamp_source="lds-01-serial",
        publish_unix_ns=scan_unix_ns,
    )
    return ExteroceptionSample.create(lidar=[lidar])


def test_step_pushes_once_per_revolution() -> None:
    samples = [
        _scan(scan_unix_ns=10, new_data=True),
        _scan(scan_unix_ns=10, new_data=False),
        _scan(scan_unix_ns=10, new_data=False),
    ]
    empty = _Feed([])

    class _Inputs:
        scan = _Feed(samples)
        imu = empty
        battery = empty
        joints = empty
        sensor_state = empty

    process_module.inputs = _Inputs()
    process_module.outputs = type(
        "Outputs",
        (),
        {"cmd_vel": type("Sink", (), {"write": lambda self, ctx, value: None})()},
    )()
    proc = Process()
    proc._settings = {  # noqa: SLF001
        "base_frame": "base_link",
        "max_range_m": 3.5,
        "wheel_joint_name_substrings": ["wheel"],
    }
    proc._viz = _RecordingViz()  # noqa: SLF001
    from kt_turtlebot3_host.telemetry import TelemetryAccumulator

    proc._telemetry = TelemetryAccumulator(wheel_joint_name_substrings=["wheel"])  # noqa: SLF001

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = proc.step(object())  # type: ignore[arg-type]

    assert result == KT.NextStep.CONTINUE
    assert buffer.getvalue() == ""
    assert len(proc._viz.scan_pushes) == 1  # noqa: SLF001
    assert proc._viz.scan_pushes[0]["scan_unix_ns"] == 10  # noqa: SLF001
    assert len(proc._viz.telemetry_pushes) == 1  # noqa: SLF001


def main() -> None:
    test_step_pushes_once_per_revolution()
    print("Web gating tests passed")


if __name__ == "__main__":
    main()
