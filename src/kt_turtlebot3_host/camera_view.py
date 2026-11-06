"""Turn one Annex-B H.264 access unit into a JPEG for the camera frame.

The live decoder uses the KTM libav libraries already loaded with this process.
It does not open a camera, a serial port, or an ffmpeg program.
"""

from __future__ import annotations

import base64
import ctypes


class H264DecodeError(RuntimeError):
    """This access unit did not become a picture."""


class LiveDecoderUnproven(H264DecodeError):
    """KTM libav could not be loaded in this process."""


class JpegDecoder:
    def to_jpeg(self, *, data: bytes, codec_header: bytes) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        return None


class KnownBufferDecoder(JpegDecoder):
    """Test double. One known access unit becomes one known JPEG."""

    def __init__(self, *, access_unit: bytes, jpeg: bytes) -> None:
        self._access_unit = bytes(access_unit)
        self._jpeg = bytes(jpeg)
        self.calls = 0

    def to_jpeg(self, *, data: bytes, codec_header: bytes) -> bytes:
        del codec_header
        self.calls += 1
        if bytes(data) != self._access_unit:
            raise ValueError("unknown access unit")
        return self._jpeg


# ffmpeg 4.4.4 field offsets on aarch64. The KTM store pins this build.
_CTX_QUALITY = 68
_CTX_FLAGS = 76
_CTX_TIME_BASE = 100
_CTX_WIDTH = 116
_CTX_HEIGHT = 120
_CTX_PIX_FMT = 136
_FRAME_LINESIZE = 64
_FRAME_WIDTH = 104
_FRAME_HEIGHT = 108
_FRAME_FORMAT = 116
_PKT_DATA = 24
_PKT_SIZE = 32
_H264 = 27
_MJPEG = 7
_YUVJ420P = 12
_QSCALE = 2
_EAGAIN = -11
_LOG_QUIET = -8
_QP2LAMBDA = 118
_JPEG_QSCALE = 5


def _has_sps(data: bytes) -> bool:
    index = 0
    size = len(data)
    while index + 4 < size:
        if data[index] == 0 and data[index + 1] == 0 and data[index + 2] == 0 and data[index + 3] == 1:
            if index + 4 < size and (data[index + 4] & 0x1F) == 7:
                return True
            index += 4
            continue
        if data[index] == 0 and data[index + 1] == 0 and data[index + 2] == 1:
            if (data[index + 3] & 0x1F) == 7:
                return True
            index += 3
            continue
        index += 1
    return False


def _i32(addr: int, offset: int, value: int | None = None) -> int:
    slot = ctypes.c_int32.from_address(addr + offset)
    if value is not None:
        slot.value = value
    return int(slot.value)


class LibavJpegDecoder(JpegDecoder):
    """Decode Annex-B H.264 with libavcodec and encode one JPEG."""

    def __init__(self) -> None:
        self._load_error: OSError | None = None
        self._codec = None
        self._util = None
        self._sws = None
        self._decoder = None
        self._decoder_id = 0
        self._jpeg = None
        self._jpeg_key: tuple[int, int] | None = None
        self._sws_ctx = None
        self._sws_key: tuple[int, int, int] | None = None
        self._packet = None
        self._frame = None
        self._seen_sps = False
        try:
            self._load()
        except OSError as exc:
            self._load_error = exc

    def close(self) -> None:
        codec = self._codec
        if codec is None:
            return
        self._free_ptr(self._sws_ctx, self._sws.sws_freeContext if self._sws else None)
        self._sws_ctx = None
        self._free_context(self._decoder)
        self._free_context(self._jpeg)
        self._decoder = None
        self._jpeg = None
        if self._packet is not None:
            holder = ctypes.c_void_p(self._packet)
            codec.av_packet_free(ctypes.byref(holder))
            self._packet = None
        if self._frame is not None:
            holder = ctypes.c_void_p(self._frame)
            self._util.av_frame_free(ctypes.byref(holder))
            self._frame = None

    def to_jpeg(self, *, data: bytes, codec_header: bytes) -> bytes:
        if self._load_error is not None or self._codec is None:
            detail = self._load_error if self._load_error is not None else "libavcodec was not loaded"
            raise LiveDecoderUnproven(
                "KTM libav H.264 decode is not available in this process: "
                f"{detail}"
            )
        payload = bytes(data)
        header = bytes(codec_header)
        if header and not _has_sps(payload) and not self._seen_sps:
            payload = header + payload
        if _has_sps(payload):
            self._seen_sps = True
        if not payload:
            raise H264DecodeError("camera access unit is empty")
        self._ensure_decoder()
        picture = self._decode(payload)
        if picture is None:
            raise H264DecodeError("H.264 decoder produced no picture for this access unit")
        try:
            return self._encode_jpeg(picture)
        finally:
            self._util.av_frame_unref(picture)

    def _load(self) -> None:
        mode = ctypes.RTLD_GLOBAL
        util = ctypes.CDLL("libavutil.so.56", mode=mode)
        codec = ctypes.CDLL("libavcodec.so.58", mode=mode)
        sws = ctypes.CDLL("libswscale.so.5", mode=mode)
        util.av_log_set_level.argtypes = [ctypes.c_int]
        util.av_log_set_level(_LOG_QUIET)
        util.av_frame_alloc.restype = ctypes.c_void_p
        util.av_frame_free.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        util.av_frame_unref.argtypes = [ctypes.c_void_p]
        util.av_frame_get_buffer.argtypes = [ctypes.c_void_p, ctypes.c_int]
        util.av_frame_get_buffer.restype = ctypes.c_int
        for name in ("avcodec_find_decoder", "avcodec_find_encoder"):
            fn = getattr(codec, name)
            fn.argtypes = [ctypes.c_int]
            fn.restype = ctypes.c_void_p
        codec.avcodec_alloc_context3.argtypes = [ctypes.c_void_p]
        codec.avcodec_alloc_context3.restype = ctypes.c_void_p
        codec.avcodec_open2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        codec.avcodec_open2.restype = ctypes.c_int
        codec.avcodec_free_context.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        codec.avcodec_send_packet.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        codec.avcodec_send_packet.restype = ctypes.c_int
        codec.avcodec_receive_frame.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        codec.avcodec_receive_frame.restype = ctypes.c_int
        codec.avcodec_send_frame.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        codec.avcodec_send_frame.restype = ctypes.c_int
        codec.avcodec_receive_packet.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        codec.avcodec_receive_packet.restype = ctypes.c_int
        codec.av_packet_alloc.restype = ctypes.c_void_p
        codec.av_new_packet.argtypes = [ctypes.c_void_p, ctypes.c_int]
        codec.av_new_packet.restype = ctypes.c_int
        codec.av_packet_unref.argtypes = [ctypes.c_void_p]
        codec.av_packet_free.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        if hasattr(codec, "avcodec_register_all"):
            codec.avcodec_register_all()
        sws.sws_getContext.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ]
        sws.sws_getContext.restype = ctypes.c_void_p
        sws.sws_scale.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_int),
        ]
        sws.sws_scale.restype = ctypes.c_int
        sws.sws_freeContext.argtypes = [ctypes.c_void_p]
        self._util = util
        self._codec = codec
        self._sws = sws
        self._packet = codec.av_packet_alloc()
        self._frame = util.av_frame_alloc()
        if not self._packet or not self._frame:
            raise OSError("libav could not allocate a packet or a frame")

    def _ensure_decoder(self) -> None:
        if self._decoder is not None:
            return
        codec_impl = self._codec.avcodec_find_decoder(_H264)
        if not codec_impl:
            raise H264DecodeError("libavcodec has no H.264 decoder")
        ctx = self._codec.avcodec_alloc_context3(codec_impl)
        if not ctx:
            raise H264DecodeError("libavcodec could not allocate an H.264 decoder")
        if self._codec.avcodec_open2(ctx, codec_impl, None) < 0:
            self._free_context(ctx)
            raise H264DecodeError("libavcodec could not open the H.264 decoder")
        self._decoder = ctx

    def _decode(self, payload: bytes) -> ctypes.c_void_p | None:
        codec = self._codec
        codec.av_packet_unref(self._packet)
        if codec.av_new_packet(self._packet, len(payload)) < 0:
            raise H264DecodeError("libav could not allocate an H.264 packet")
        base = ctypes.cast(self._packet, ctypes.c_void_p).value
        data_ptr = ctypes.c_void_p.from_address(base + _PKT_DATA).value
        ctypes.memmove(data_ptr, payload, len(payload))
        self._util.av_frame_unref(self._frame)
        sent = codec.avcodec_send_packet(self._decoder, self._packet)
        if sent < 0 and sent != _EAGAIN:
            codec.av_packet_unref(self._packet)
            raise H264DecodeError(f"H.264 send failed ({sent})")
        got = codec.avcodec_receive_frame(self._decoder, self._frame)
        codec.av_packet_unref(self._packet)
        if got == _EAGAIN or got < 0:
            return None
        return self._frame

    def _encode_jpeg(self, frame: ctypes.c_void_p) -> bytes:
        width = _i32(frame, _FRAME_WIDTH)
        height = _i32(frame, _FRAME_HEIGHT)
        src_fmt = _i32(frame, _FRAME_FORMAT)
        if width < 1 or height < 1:
            raise H264DecodeError("decoded picture has no dimensions")
        dst = self._jpeg_frame(width, height, src_fmt)
        self._ensure_jpeg(width, height)
        codec = self._codec
        sent = codec.avcodec_send_frame(self._jpeg, dst)
        holder = ctypes.c_void_p(dst)
        self._util.av_frame_free(ctypes.byref(holder))
        if sent < 0:
            raise H264DecodeError(f"JPEG send failed ({sent})")
        codec.av_packet_unref(self._packet)
        got = codec.avcodec_receive_packet(self._jpeg, self._packet)
        if got < 0:
            raise H264DecodeError(f"JPEG receive failed ({got})")
        base = ctypes.cast(self._packet, ctypes.c_void_p).value
        ptr = ctypes.c_void_p.from_address(base + _PKT_DATA).value
        size = _i32(base, _PKT_SIZE)
        if size < 4 or not ptr:
            codec.av_packet_unref(self._packet)
            raise H264DecodeError("JPEG encoder returned an empty packet")
        jpeg = ctypes.string_at(ptr, size)
        codec.av_packet_unref(self._packet)
        if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
            raise H264DecodeError("JPEG encoder did not return a JPEG")
        return jpeg

    def _jpeg_frame(self, width: int, height: int, src_fmt: int) -> ctypes.c_void_p:
        dst = self._util.av_frame_alloc()
        if not dst:
            raise H264DecodeError("libav could not allocate a JPEG frame")
        _i32(dst, _FRAME_WIDTH, width)
        _i32(dst, _FRAME_HEIGHT, height)
        _i32(dst, _FRAME_FORMAT, _YUVJ420P)
        if self._util.av_frame_get_buffer(dst, 32) < 0:
            holder = ctypes.c_void_p(dst)
            self._util.av_frame_free(ctypes.byref(holder))
            raise H264DecodeError("libav could not allocate JPEG picture memory")
        key = (width, height, src_fmt)
        if self._sws_ctx is None or self._sws_key != key:
            if self._sws_ctx is not None:
                self._sws.sws_freeContext(self._sws_ctx)
            self._sws_ctx = self._sws.sws_getContext(
                width, height, src_fmt, width, height, _YUVJ420P, 1, None, None, None,
            )
            self._sws_key = key
        if not self._sws_ctx:
            holder = ctypes.c_void_p(dst)
            self._util.av_frame_free(ctypes.byref(holder))
            raise H264DecodeError(f"libswscale could not convert pixel format {src_fmt}")
        src_planes, src_stride = _planes(self._frame)
        dst_planes, dst_stride = _planes(dst)
        scaled = self._sws.sws_scale(
            self._sws_ctx, src_planes, src_stride, 0, height, dst_planes, dst_stride,
        )
        if scaled <= 0:
            holder = ctypes.c_void_p(dst)
            self._util.av_frame_free(ctypes.byref(holder))
            raise H264DecodeError("libswscale did not convert the picture")
        return dst

    def _ensure_jpeg(self, width: int, height: int) -> None:
        if self._jpeg is not None and self._jpeg_key == (width, height):
            return
        self._free_context(self._jpeg)
        self._jpeg = None
        impl = self._codec.avcodec_find_encoder(_MJPEG)
        if not impl:
            raise H264DecodeError("libavcodec has no MJPEG encoder")
        ctx = self._codec.avcodec_alloc_context3(impl)
        if not ctx:
            raise H264DecodeError("libavcodec could not allocate an MJPEG encoder")
        _i32(ctx, _CTX_QUALITY, _QP2LAMBDA * _JPEG_QSCALE)
        _i32(ctx, _CTX_FLAGS, _i32(ctx, _CTX_FLAGS) | _QSCALE)
        _i32(ctx, _CTX_TIME_BASE, 1)
        _i32(ctx, _CTX_TIME_BASE + 4, 15)
        _i32(ctx, _CTX_WIDTH, width)
        _i32(ctx, _CTX_HEIGHT, height)
        _i32(ctx, _CTX_PIX_FMT, _YUVJ420P)
        if self._codec.avcodec_open2(ctx, impl, None) < 0:
            self._free_context(ctx)
            raise H264DecodeError("libavcodec could not open the MJPEG encoder")
        self._jpeg = ctx
        self._jpeg_key = (width, height)

    def _free_context(self, ctx: ctypes.c_void_p | None) -> None:
        if not ctx or self._codec is None:
            return
        holder = ctypes.c_void_p(ctx)
        self._codec.avcodec_free_context(ctypes.byref(holder))

    def _free_ptr(self, ptr: ctypes.c_void_p | None, freer: object) -> None:
        if ptr and freer is not None:
            freer(ptr)


def _planes(frame: ctypes.c_void_p) -> tuple[object, object]:
    base = ctypes.cast(frame, ctypes.c_void_p).value or 0
    planes = (ctypes.c_void_p * 4)()
    stride = (ctypes.c_int * 4)()
    for index in range(4):
        planes[index] = ctypes.c_void_p.from_address(base + index * 8).value
        stride[index] = ctypes.c_int.from_address(base + _FRAME_LINESIZE + index * 4).value
    return planes, stride


def camera_jpeg_message(*, frame_number: int, jpeg: bytes) -> dict[str, object]:
    return {
        "type": "camera_jpeg",
        "frame_number": int(frame_number),
        "jpeg_base64": base64.b64encode(jpeg).decode("ascii"),
    }
