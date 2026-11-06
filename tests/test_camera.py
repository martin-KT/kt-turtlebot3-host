"""Camera samples reach the page sink only when frame_number changes."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import kt_process as KT
from kt.messages.exteroception_sample import ExteroceptionSample, Lidar, Transform, Vector3
from kt.messages.vision_sample import CompressionFormat, ImageSample, MediaPipeline

import kt_turtlebot3_host.process as process_module
from kt_turtlebot3_host.camera_view import (
    H264DecodeError,
    KnownBufferDecoder,
    LibavJpegDecoder,
    camera_jpeg_message,
)
from kt_turtlebot3_host.process import Process
from kt_turtlebot3_host.web_viz import WebVizService

_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000"
    "ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c"
    "20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432"
    "ffc0000b080001000101011100"
    "ffc4001f0000010501010101010100000000000000000102030405060708090a0b"
    "ffda000c03010002110311003f00f7fa28a2803f"
    "ffd9"
)
_UNIT = b"access-unit-1"
_ROOT = Path(__file__).resolve().parents[1]


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
        self.camera_pushes: list[dict[str, object]] = []

    def push_scan(self, payload: dict[str, object]) -> None:
        self.scan_pushes.append(payload)

    def push_telemetry(self, payload: dict[str, object]) -> None:
        self.telemetry_pushes.append(payload)

    def push_camera(self, *, frame_number: int, jpeg: bytes) -> None:
        self.camera_pushes.append({"frame_number": frame_number, "jpeg": jpeg})

    def cmd_vel(self) -> tuple[float, float]:
        return (0.0, 0.0)


def _scan() -> ExteroceptionSample:
    lidar = Lidar.create(
        source="base_scan",
        data=[1.0] * 360 + [0.0] * 360,
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
        new_data_flag=True,
        scan_unix_ns=10,
        scan_timestamp_source="lds-01-serial",
        publish_unix_ns=10,
    )
    return ExteroceptionSample.create(lidar=[lidar])


def _image(*, frame_number: int, payload: bytes = _UNIT) -> ImageSample:
    return ImageSample.create(
        source="pi-camera",
        data=payload,
        codec_header=b"sps-pps",
        compression=CompressionFormat.H264,
        pipeline=MediaPipeline.OTHER,
        frame_number=frame_number,
        captured_unix_ns=frame_number,
        data_shape=[480, 640],
    )


def _install(*, scans: list[object], cameras: list[object]) -> None:
    empty = _Feed([])

    class _Inputs:
        scan = _Feed(scans)
        camera = _Feed(cameras)
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


def _ready(decoder: object) -> tuple[Process, _RecordingViz]:
    proc = Process(decoder=decoder)  # type: ignore[arg-type]
    viz = _RecordingViz()
    proc._settings = {  # noqa: SLF001
        "base_frame": "base_link",
        "max_range_m": 3.5,
        "wheel_joint_name_substrings": ["wheel"],
    }
    proc._viz = viz  # noqa: SLF001
    from kt_turtlebot3_host.telemetry import TelemetryAccumulator

    proc._telemetry = TelemetryAccumulator(wheel_joint_name_substrings=["wheel"])  # noqa: SLF001
    return proc, viz


def test_new_frame_reaches_the_page_and_a_repeat_does_not() -> None:
    decoder = KnownBufferDecoder(access_unit=_UNIT, jpeg=_JPEG)
    _install(
        scans=[_scan()],
        cameras=[_image(frame_number=7), _image(frame_number=7), _image(frame_number=8, payload=_UNIT)],
    )
    proc, viz = _ready(decoder)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert proc.step(object()) == KT.NextStep.CONTINUE  # type: ignore[arg-type]
    assert buffer.getvalue() == ""
    assert len(viz.scan_pushes) == 1
    assert [item["frame_number"] for item in viz.camera_pushes] == [7, 8]
    assert viz.camera_pushes[0]["jpeg"] == _JPEG
    assert decoder.calls == 2


def test_tick_without_camera_still_publishes_scans() -> None:
    _install(scans=[_scan(), _scan()], cameras=[])
    proc, viz = _ready(KnownBufferDecoder(access_unit=_UNIT, jpeg=_JPEG))
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert proc.step(object()) == KT.NextStep.CONTINUE  # type: ignore[arg-type]
    assert buffer.getvalue() == ""
    assert viz.camera_pushes == []
    assert len(viz.scan_pushes) == 2


_IDR = bytes.fromhex(
    "0000000127640028ac2b40501ed080000003008000001e7050003d090000bebc"
    "def700f1226a0000000128ee025cb000000001258880203fff9401b15b0f9941"
    "a34b9a64b81efef16064a5c81921f2276000000300003a708b9d400146003830"
    "171809f805180000030000030000030000030000030000030000030000030000"
    "0300000300000300000300000300000300000300000300000300000300000300"
    "00030000030039e0"
)
_SPS = bytes.fromhex(
    "0000000127640028ac2b40501ed080000003008000001e7050003d090000bebcdef700f1226a"
    "0000000128ee025cb0"
)


def test_bad_access_unit_does_not_print_or_push() -> None:
    _install(scans=[_scan()], cameras=[_image(frame_number=1)])
    proc, viz = _ready(LibavJpegDecoder())
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert proc.step(object()) == KT.NextStep.CONTINUE  # type: ignore[arg-type]
    assert buffer.getvalue() == ""
    assert viz.camera_pushes == []
    assert proc._camera_decoder_error  # noqa: SLF001
    decoder = LibavJpegDecoder()
    try:
        try:
            decoder.to_jpeg(data=b"x", codec_header=b"y")
            raise AssertionError("a broken access unit must not become a JPEG")
        except H264DecodeError:
            pass
    finally:
        decoder.close()


def test_annexb_idr_becomes_a_640x480_jpeg() -> None:
    decoder = LibavJpegDecoder()
    try:
        jpeg = decoder.to_jpeg(data=_IDR, codec_header=_SPS)
    finally:
        decoder.close()
    assert jpeg.startswith(b"\xff\xd8") and jpeg.endswith(b"\xff\xd9")
    sof = jpeg.find(b"\xff\xc0")
    assert sof > 0
    height = int.from_bytes(jpeg[sof + 5 : sof + 7], "big")
    width = int.from_bytes(jpeg[sof + 7 : sof + 9], "big")
    assert (width, height) == (640, 480)
    assert len(jpeg) < 50_000


def test_camera_message_is_separate_from_scan_state() -> None:
    message = camera_jpeg_message(frame_number=3, jpeg=_JPEG)
    assert message["type"] == "camera_jpeg"
    assert message["frame_number"] == 3
    assert _JPEG[:2] == b"\xff\xd8" and _JPEG[-2:] == b"\xff\xd9"
    service = WebVizService({"telemetry_push_hz": 20})
    service.push_scan({"scan_unix_ns": 10, "points": []})
    before = service.latest_scan()
    service.push_camera(frame_number=3, jpeg=_JPEG)
    assert service.latest_scan() == before
    assert service.latest_camera() == message
    assert "type" not in (before or {})


def test_page_layout_keeps_lidar_and_adds_a_matching_camera_frame() -> None:
    page = (_ROOT / "src/kt_turtlebot3_host/static/index.html").read_text(encoding="utf-8")
    script = (_ROOT / "src/kt_turtlebot3_host/static/viz.js").read_text(encoding="utf-8")
    runtime = json.loads((_ROOT / "runtime.json").read_text(encoding="utf-8"))
    assert 'id="viz"' in page
    assert 'id="camera"' in page
    assert 'id="imu-panel"' in page
    assert 'id="imu-traces"' in page
    assert 'id="main-panel"' in page
    assert 'id="camera-wrap"' in page
    assert "object-fit: contain" in page
    assert "aspect-ratio: 4 / 3" in page
    assert "--imu-panel-height: 20%" in page
    assert "width: 25%" in page
    assert "@media (max-width: 900px)" in page
    assert page.index('id="imu-traces"') > page.index("</aside>")
    assert "position: absolute" in page
    assert 'msg.type === "camera_jpeg"' in script
    assert runtime["config"]["http_port"] == 8765
    assert runtime["transport"]["kt_lan"]["routes"]["camera"]["addr"] == "192.168.0.101:48110"


def main() -> None:
    test_new_frame_reaches_the_page_and_a_repeat_does_not()
    test_tick_without_camera_still_publishes_scans()
    test_bad_access_unit_does_not_print_or_push()
    test_annexb_idr_becomes_a_640x480_jpeg()
    test_camera_message_is_separate_from_scan_state()
    test_page_layout_keeps_lidar_and_adds_a_matching_camera_frame()
    print("Host camera tests passed")


if __name__ == "__main__":
    main()
