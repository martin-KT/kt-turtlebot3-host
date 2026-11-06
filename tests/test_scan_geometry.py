"""Geometry from ExteroceptionSample lidar beams."""

from __future__ import annotations

import math

from kt.messages.exteroception_sample import ExteroceptionSample, Lidar, Transform, Vector3

from kt_turtlebot3_host.scan_geometry import lidar_to_points, lidar_to_payload, publish_scan_if_new


def _lidar(
    *,
    ranges: list[float],
    intensities: list[float] | None = None,
    new_data: bool = True,
    scan_unix_ns: int = 1,
    mount_x: float = 0.0,
    mount_y: float = 0.0,
    yaw: float = 0.0,
) -> Lidar:
    if intensities is None:
        intensities = [100.0] * len(ranges)
    data = list(ranges) + list(intensities)
    construction = Lidar.create(
        source="base_scan",
        data=data,
        data_shape=[2, len(ranges)],
        horizontal_angular_resolution=(2.0 * math.pi) / len(ranges),
        horizontal_start_angle=0.0,
        horizontal_end_angle=2.0 * math.pi - (2.0 * math.pi) / len(ranges),
        scan_duration=200_000_000,
        time_between_scans=200_000_000,
        transform=Transform.create(
            position=Vector3.create(x=mount_x, y=mount_y, z=0.0),
            euler_angles=Vector3.create(x=0.0, y=0.0, z=yaw),
            link_name="base_scan",
            part="base_link",
        ),
        new_data_flag=new_data,
        scan_unix_ns=scan_unix_ns,
        scan_timestamp_source="test",
        publish_unix_ns=scan_unix_ns,
    )
    sample = ExteroceptionSample.create(lidar=[construction])
    return sample.lidar[0]


class _Recorder:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def push_scan(self, payload: dict[str, object]) -> None:
        self.payloads.append(payload)


def test_beam_zero_along_forward_with_mount_offset() -> None:
    ranges = [float("nan")] * 360
    ranges[0] = 2.0
    points = lidar_to_points(_lidar(ranges=ranges, mount_x=-0.064), range_max_m=3.5)
    assert len(points) == 1
    x, y, intensity = points[0]
    assert abs(x - (2.0 - 0.064)) < 1e-4
    assert abs(y) < 1e-4
    assert intensity == 100.0


def test_beam_90_is_left_in_base_link() -> None:
    # HLDS index increases clockwise; +Y (left) is index 270 (same metadata as driver).
    ranges = [0.0] * 360
    ranges[270] = 1.0
    points = lidar_to_points(_lidar(ranges=ranges), range_max_m=3.5)
    assert len(points) == 1
    x, y, _ = points[0]
    assert abs(x) < 0.05
    assert abs(y - 1.0) < 0.05


def test_invalid_and_out_of_range_beams_skipped() -> None:
    ranges = [1.0, 0.0, float("nan"), 0.05, 4.0]
    points = lidar_to_points(
        _lidar(ranges=ranges),
        range_min_m=0.12,
        range_max_m=3.5,
    )
    assert len(points) == 1
    assert abs(points[0][0] - 1.0) < 1e-4
    assert abs(points[0][1]) < 1e-4


def test_payload_includes_metadata() -> None:
    lidar = _lidar(ranges=[1.0] + [0.0] * 359, scan_unix_ns=42)
    payload = lidar_to_payload(lidar, base_frame="base_link", range_max_m=3.5)
    assert payload["scan_unix_ns"] == 42
    assert payload["frame"] == "base_link"
    assert payload["link"] == "base_scan"
    assert isinstance(payload["points"], list)


def test_geometry_after_exteroception_wire_round_trip() -> None:
    ranges = [0.0] * 360
    ranges[0] = 2.0
    sample = ExteroceptionSample.create(lidar=[_lidar(ranges=ranges)])
    decoded = ExteroceptionSample.from_bytes(sample.encoded())
    lidar = decoded.lidar[0]
    points = lidar_to_points(lidar, range_max_m=3.5)
    assert len(points) >= 1
    payload = lidar_to_payload(lidar, base_frame="base_link", range_max_m=3.5)
    assert len(payload["points"]) >= 1


def test_publish_only_when_new_data_flag() -> None:
    ranges = [1.0] * 4
    sample_new = ExteroceptionSample.create(lidar=[_lidar(ranges=ranges, new_data=True)])
    sample_old = ExteroceptionSample.create(lidar=[_lidar(ranges=ranges, new_data=False)])
    rec = _Recorder()
    assert publish_scan_if_new(sample_new, rec, base_frame="base_link", max_range_m=3.5)
    assert not publish_scan_if_new(sample_old, rec, base_frame="base_link", max_range_m=3.5)
    assert len(rec.payloads) == 1


def main() -> None:
    test_beam_zero_along_forward_with_mount_offset()
    test_beam_90_is_left_in_base_link()
    test_invalid_and_out_of_range_beams_skipped()
    test_payload_includes_metadata()
    test_geometry_after_exteroception_wire_round_trip()
    test_publish_only_when_new_data_flag()
    print("Scan geometry tests passed")


if __name__ == "__main__":
    main()
