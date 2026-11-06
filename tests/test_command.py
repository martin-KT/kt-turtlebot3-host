"""Zero cmd_vel stays zero and each publish is a new sample."""

from __future__ import annotations

from kt_turtlebot3_host.command import velocity_command, zero_command


def test_velocity_command_maps_linear_x_and_angular_z() -> None:
    sample = velocity_command(
        linear_x=0.11,
        angular_z=-0.5,
        sequence=3,
        emitted_unix_ns=100,
    )
    tv = sample.locomotion.translational_velocity
    rv = sample.locomotion.rotational_velocity
    assert abs(float(tv.x) - 0.11) < 1e-6
    assert abs(float(tv.y)) < 1e-6
    assert abs(float(rv.z) - (-0.5)) < 1e-6
    assert sample.sequence == 3


def test_zero_command_is_stationary_and_sequences_differ() -> None:
    first = zero_command(sequence=1, emitted_unix_ns=10)
    second = zero_command(sequence=2, emitted_unix_ns=20)
    assert first.locomotion.translational_velocity.x == 0.0
    assert first.locomotion.translational_velocity.y == 0.0
    assert first.locomotion.translational_velocity.z == 0.0
    assert first.locomotion.rotational_velocity.x == 0.0
    assert first.locomotion.rotational_velocity.y == 0.0
    assert first.locomotion.rotational_velocity.z == 0.0
    assert first.sequence == 1
    assert second.sequence == 2
    assert first.emitted_unix_ns != second.emitted_unix_ns
    assert first.expires_unix_ns == 0


def main() -> None:
    test_velocity_command_maps_linear_x_and_angular_z()
    test_zero_command_is_stationary_and_sequences_differ()
    print("Host command tests passed")


if __name__ == "__main__":
    main()
