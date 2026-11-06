"""Host scan lines. No network."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import kt_process as KT
from kt.messages.exteroception_sample import (
    Compass,
    ExteroceptionSample,
    IMU,
    Lidar,
    Transform,
    Vector3,
    Vector4,
)

import kt_turtlebot3_host.process as process_module
from kt_turtlebot3_host.process import Process
from kt_turtlebot3_host.report import (
    format_imu,
    format_scan,
    imu_console_line,
    imu_sidebar_dict_from_item,
)


class _Received:
    def __init__(self, value: object, *, remote_time_ns: int | None = None) -> None:
        self.value = value
        self.remote_time_ns = remote_time_ns


class _Feed:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def read_all(self, ctx: object) -> list[_Received]:
        del ctx
        return [_Received(value) for value in self._values]


def _scan(*, scan_unix_ns: int, new_data: bool, ranges: list[float]) -> ExteroceptionSample:
    intensities = [0.0] * len(ranges)
    lidar = Lidar.create(
        source="base_scan",
        data=ranges + intensities,
        data_shape=[2, len(ranges)],
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


def test_line_shows_time_flag_beams_and_four_ranges() -> None:
    ranges = [0.0] * 360
    ranges[0] = 1.25
    ranges[90] = 2.5
    ranges[180] = 0.12
    ranges[270] = 3.5
    line = format_scan(_scan(scan_unix_ns=123, new_data=True, ranges=ranges))
    assert line == (
        "scan_unix_ns=123 new=true beams=360 link=base_scan "
        "r0=1.250 r90=2.500 r180=0.120 r270=3.500"
    )


def test_repeated_revolution_is_marked() -> None:
    ranges = [1.0] * 360
    line = format_scan(_scan(scan_unix_ns=50, new_data=False, ranges=ranges))
    assert "new=false" in line
    assert line.startswith("scan_unix_ns=50 ")


def test_empty_sample_is_visible() -> None:
    assert format_scan(ExteroceptionSample.create(lidar=[])) == "scan empty"


_IMU_LINE = (
    "imu gyro=0.0100,0.0200,0.0300 "
    "acc=0.0000,0.0000,9.8000 "
    "quat=1.0000,0.0000,0.0000,0.0000 "
    "mag=0.1000,0.2000,0.3000"
)


def _full_imu_sample() -> ExteroceptionSample:
    return ExteroceptionSample.create(
        imu=[
            IMU.create(
                source="imu_link",
                gyro=Vector3.create(x=0.01, y=0.02, z=0.03),
                acc=Vector3.create(x=0.0, y=0.0, z=9.8),
                orientation_quat=Vector4.create(w=1.0, x=0.0, y=0.0, z=0.0),
                has_acc=True,
                has_gyro=True,
                has_orientation_quat=True,
                orientation_frame_id="imu_link",
            )
        ],
        compass=Compass.create(
            source="imu_link",
            mag=Vector3.create(x=0.1, y=0.2, z=0.3),
        ),
    )


def test_imu_line_matches_opencr_and_gateway_format() -> None:
    sample = _full_imu_sample()
    assert imu_console_line(sample) == _IMU_LINE
    assert format_imu(_Received(sample)) == _IMU_LINE
    sidebar = imu_sidebar_dict_from_item(_Received(sample))
    assert sidebar is not None
    assert abs(float(sidebar["gyro"]["z"]) - 0.03) < 1e-4  # type: ignore[index]
    assert abs(float(sidebar["acc"]["z"]) - 9.8) < 1e-3  # type: ignore[index]
    assert sidebar["has_gyro"] is True


def test_imu_line_skips_incomplete_sample() -> None:
    partial = ExteroceptionSample.create(
        imu=[
            IMU.create(
                source="imu_link",
                gyro=Vector3.create(x=0.01, y=0.02, z=0.03),
            )
        ]
    )
    assert imu_console_line(partial) is None


class _NoopViz:
    def push_scan(self, payload: object) -> None:
        del payload

    def push_telemetry(self, payload: object) -> None:
        del payload

    def cmd_vel(self) -> tuple[float, float]:
        return (0.0, 0.0)


def _process_ready_for_step() -> Process:
    proc = Process()
    proc._settings = {  # noqa: SLF001
        "base_frame": "base_link",
        "max_range_m": 3.5,
        "wheel_joint_name_substrings": ["wheel"],
    }
    proc._viz = _NoopViz()  # noqa: SLF001
    from kt_turtlebot3_host.telemetry import TelemetryAccumulator

    proc._telemetry = TelemetryAccumulator(wheel_joint_name_substrings=["wheel"])  # noqa: SLF001
    return proc


class _CommandSink:
    def __init__(self) -> None:
        self.written: list[object] = []

    def write(self, ctx: object, value: object) -> None:
        del ctx
        self.written.append(value)


def _install_channels(
    scan_values: list[object],
    *,
    imu_values: list[object] | None = None,
) -> _CommandSink:
    sink = _CommandSink()
    empty = _Feed([])

    class _Inputs:
        scan = _Feed(scan_values)
        imu = _Feed(imu_values or [])
        battery = empty
        joints = empty
        sensor_state = empty

    process_module.inputs = _Inputs()
    process_module.outputs = type("Outputs", (), {"cmd_vel": sink})()
    return sink


def test_step_does_not_print_scans() -> None:
    ranges = [1.0] * 360
    samples = [
        _scan(scan_unix_ns=1, new_data=True, ranges=ranges),
        _scan(scan_unix_ns=1, new_data=False, ranges=ranges),
    ]
    _install_channels(samples)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = _process_ready_for_step().step(object())  # type: ignore[arg-type]
    assert result == KT.NextStep.CONTINUE
    assert buffer.getvalue() == ""


def test_step_does_not_print_imu_to_console() -> None:
    _install_channels([], imu_values=[_full_imu_sample()])
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = _process_ready_for_step().step(object())  # type: ignore[arg-type]
    assert result == KT.NextStep.CONTINUE
    assert buffer.getvalue() == ""


def test_idle_step_prints_nothing() -> None:
    sink = _install_channels([])
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = _process_ready_for_step().step(object())  # type: ignore[arg-type]
    assert result == KT.NextStep.CONTINUE
    assert buffer.getvalue() == ""
    assert len(sink.written) == 1
    assert abs(float(sink.written[0].locomotion.translational_velocity.x)) < 1e-6
    assert abs(float(sink.written[0].locomotion.rotational_velocity.z)) < 1e-6
    assert sink.written[0].emitted_unix_ns == 0


def main() -> None:
    test_line_shows_time_flag_beams_and_four_ranges()
    test_repeated_revolution_is_marked()
    test_empty_sample_is_visible()
    test_imu_line_matches_opencr_and_gateway_format()
    test_imu_line_skips_incomplete_sample()
    test_step_does_not_print_scans()
    test_step_does_not_print_imu_to_console()
    test_idle_step_prints_nothing()
    print("Host scan report tests passed")


if __name__ == "__main__":
    main()
