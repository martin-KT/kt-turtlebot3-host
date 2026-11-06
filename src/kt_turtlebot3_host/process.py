"""Read the robot gateway scan on kt_lan and update the browser viz."""

from __future__ import annotations

import kt_process as KT

from ._generated.channels import inputs, outputs
from .camera_view import H264DecodeError, JpegDecoder, LibavJpegDecoder
from .command import velocity_command
from .report import imu_sidebar_dict_from_item
from .scan_geometry import publish_scan_if_new, settings_from_config
from .telemetry import TelemetryAccumulator, wheel_joint_filter_from_settings
from .web_viz import WebVizService


class Process(KT.Process):
    """Print one line per received scan and push new revolutions to the web UI."""

    def __init__(self, *, decoder: JpegDecoder | None = None) -> None:
        self._command_seq = 0
        self._telemetry: TelemetryAccumulator | None = None
        self._decoder = decoder
        self._camera_frame_number: int | None = None
        self._camera_decoder_error: str | None = None

    def setup(self, ctx: KT.Context) -> KT.NextStep:
        self._settings = settings_from_config(ctx.config())
        if self._decoder is None:
            self._decoder = LibavJpegDecoder()
        self._viz = WebVizService(self._settings)
        self._telemetry = TelemetryAccumulator(
            wheel_joint_name_substrings=wheel_joint_filter_from_settings(self._settings),
        )
        self._viz.start()
        return KT.NextStep.CONTINUE

    def step(self, ctx: KT.Context) -> KT.NextStep:
        accumulator = self._telemetry
        viz = self._viz
        if accumulator is not None and viz is not None:
            imu_batch = inputs.imu.read_all(ctx)
            # Debug: OpenCR-style IMU line on stdout (re-enable if needed).
            # for item in imu_batch:
            #     line = format_imu(item)
            #     if line is not None:
            #         print(line, flush=True)
            accumulator.ingest_imu_batch(imu_batch)
            if imu_batch:
                sidebar_imu = imu_sidebar_dict_from_item(imu_batch[-1])
                if sidebar_imu is not None:
                    accumulator.apply_imu(sidebar_imu, channel_item=imu_batch[-1])
            accumulator.ingest_battery_batch(inputs.battery.read_all(ctx))
            accumulator.ingest_joints_batch(inputs.joints.read_all(ctx))
            accumulator.ingest_sensor_state_batch(inputs.sensor_state.read_all(ctx))
            viz.push_telemetry(accumulator.snapshot())

        for item in inputs.scan.read_all(ctx):
            publish_scan_if_new(
                item.value,
                self._viz,
                base_frame=str(self._settings["base_frame"]),
                max_range_m=float(self._settings["max_range_m"]),
            )

        self._publish_camera(ctx)

        self._command_seq += 1
        command = getattr(outputs, "cmd_vel", None)
        viz = self._viz
        if command is not None and viz is not None:
            linear_x, angular_z = viz.cmd_vel()
            command.write(
                ctx,
                velocity_command(
                    linear_x=linear_x,
                    angular_z=angular_z,
                    sequence=self._command_seq,
                    emitted_unix_ns=0,
                ),
            )
        return KT.NextStep.CONTINUE

    def _publish_camera(self, ctx: KT.Context) -> None:
        camera = getattr(inputs, "camera", None)
        viz = getattr(self, "_viz", None)
        decoder = getattr(self, "_decoder", None)
        push = getattr(viz, "push_camera", None)
        if camera is None or decoder is None or push is None:
            return
        for item in camera.read_all(ctx):
            sample = item.value
            number = int(sample.frame_number)
            if getattr(self, "_camera_frame_number", None) == number:
                continue
            try:
                jpeg = decoder.to_jpeg(
                    data=bytes(sample.data),
                    codec_header=bytes(sample.codec_header),
                )
            except H264DecodeError as exc:
                self._camera_decoder_error = str(exc)
                continue
            self._camera_frame_number = number
            push(frame_number=number, jpeg=jpeg)

    def close(self, ctx: KT.Context) -> KT.NextStep:
        del ctx
        decoder = getattr(self, "_decoder", None)
        close_decoder = getattr(decoder, "close", None)
        if close_decoder is not None:
            close_decoder()
        if getattr(self, "_viz", None) is not None:
            self._viz.stop()
        return KT.NextStep.STOP

    def config_update(
        self, ctx: KT.Context, update: KT.ConfigUpdate
    ) -> KT.ConfigUpdateResult:
        del ctx, update
        return KT.ConfigUpdateResult.ACCEPT
