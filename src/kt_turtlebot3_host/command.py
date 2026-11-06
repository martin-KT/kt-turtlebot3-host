"""50 Hz wheel velocity commands. The robot stamps the real expiry."""

from __future__ import annotations

from kt.messages.motor_sample import MotorSample, Vector3, VelocityTarget


def velocity_command(
    *,
    linear_x: float,
    angular_z: float,
    sequence: int,
    emitted_unix_ns: int,
) -> MotorSample:
    """TurtleBot3-style cmd_vel: linear.x (m/s), angular.z (rad/s).

    emitted_unix_ns is not a wall clock for the robot. Pass 0. The gateway
    measures the gap since the last new sequence on its own clock.
    """

    return MotorSample.create(
        locomotion=VelocityTarget.create(
            translational_velocity=Vector3.create(x=float(linear_x), y=0.0, z=0.0),
            rotational_velocity=Vector3.create(x=0.0, y=0.0, z=float(angular_z)),
        ),
        emitted_unix_ns=int(emitted_unix_ns),
        sequence=int(sequence),
        expires_unix_ns=0,
    )


def zero_command(*, sequence: int, emitted_unix_ns: int) -> MotorSample:
    """linear.x and angular.z are zero, in m/s and rad/s."""

    return velocity_command(
        linear_x=0.0,
        angular_z=0.0,
        sequence=sequence,
        emitted_unix_ns=emitted_unix_ns,
    )
