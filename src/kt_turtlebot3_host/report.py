"""Console lines for lidar and IMU snapshots from the robot gateway."""

from __future__ import annotations

from .telemetry import decode_exteroception_lan_sample, decode_imu_from_exteroception

_RANGE_INDEXES = (0, 90, 180, 270)


def format_scan(sample: object) -> str:
    """Summarise beam count, a few ranges, and whether this revolution is new."""

    lidars = getattr(sample, "lidar", None)
    if not lidars:
        return "scan empty"
    lidar = lidars[0]
    shape = [int(item) for item in list(lidar.data_shape)]
    beams = shape[1] if len(shape) >= 2 else 0
    values = list(lidar.data)
    ranges = values[:beams]
    link_name = ""
    transform = lidar.transform
    if transform is not None:
        link_name = str(transform.link_name)
    parts = [
        f"scan_unix_ns={int(lidar.scan_unix_ns)}",
        f"new={str(bool(lidar.new_data_flag)).lower()}",
        f"beams={beams}",
        f"link={link_name}",
    ]
    for index in _RANGE_INDEXES:
        if index < len(ranges):
            parts.append(f"r{index}={float(ranges[index]):.3f}")
        else:
            parts.append(f"r{index}=?")
    return " ".join(parts)


def imu_console_line(sample: object) -> str | None:
    """Same line as kt-opencr-driver / kt-turtlebot3-driver when all fields are present."""

    imus = getattr(sample, "imu", None)
    if not imus:
        return None
    imu = imus[0]
    gyro = getattr(imu, "gyro", None)
    acc = getattr(imu, "acc", None)
    quat = getattr(imu, "orientation_quat", None)
    compass = getattr(sample, "compass", None)
    mag = None if compass is None else getattr(compass, "mag", None)
    if gyro is None or acc is None or quat is None or mag is None:
        return None
    gyro_text = f"{gyro.x:.4f},{gyro.y:.4f},{gyro.z:.4f}"
    acc_text = f"{acc.x:.4f},{acc.y:.4f},{acc.z:.4f}"
    quat_text = f"{quat.w:.4f},{quat.x:.4f},{quat.y:.4f},{quat.z:.4f}"
    mag_text = f"{mag.x:.4f},{mag.y:.4f},{mag.z:.4f}"
    return f"imu gyro={gyro_text} acc={acc_text} quat={quat_text} mag={mag_text}"


def imu_sidebar_dict_from_item(item: object) -> dict[str, object] | None:
    """JSON sidebar IMU from the same decode path as the console line."""

    sample = decode_exteroception_lan_sample(getattr(item, "value", item))
    if imu_console_line(sample) is None:
        return None
    imus = getattr(sample, "imu", None) or []
    if not imus:
        return None
    imu = imus[0]
    acc = getattr(imu, "acc", None)
    gyro = getattr(imu, "gyro", None)
    if acc is None or gyro is None:
        return None
    return {
        "source": str(getattr(imu, "source", "") or ""),
        "acc": {
            "x": float(getattr(acc, "x", 0.0) or 0.0),
            "y": float(getattr(acc, "y", 0.0) or 0.0),
            "z": float(getattr(acc, "z", 0.0) or 0.0),
        },
        "gyro": {
            "x": float(getattr(gyro, "x", 0.0) or 0.0),
            "y": float(getattr(gyro, "y", 0.0) or 0.0),
            "z": float(getattr(gyro, "z", 0.0) or 0.0),
        },
        "has_acc": True,
        "has_gyro": True,
    }


def format_imu(item: object) -> str | None:
    """OpenCR-style IMU line from one kt_lan imu channel delivery."""

    sample = decode_exteroception_lan_sample(getattr(item, "value", item))
    return imu_console_line(sample)
