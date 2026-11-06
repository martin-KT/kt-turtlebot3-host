from __future__ import annotations

import argparse

import kt_process as KT

from .process import Process


def main() -> None:
    parser = argparse.ArgumentParser(description="Run kt-turtlebot3-host")
    parser.add_argument("--package", required=True, help="lifecycle package manifest")
    parser.add_argument("--runtime", required=True, help="runtime configuration")
    args = parser.parse_args()
    # Standard runner handles Ctrl+C/SIGTERM and joins before cleanup.
    KT.run(args.package, args.runtime, Process())


if __name__ == "__main__":
    main()
