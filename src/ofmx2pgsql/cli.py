"""Command-line interface entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .parser import iter_ofmx_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ofmx2pgsql",
        description="Import OpenFlightMaps OFMX data into PostGIS.",
    )
    parser.add_argument(
        "--scan",
        type=Path,
        metavar="PATH",
        help="Scan a file or directory for .ofmx files and list matches.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.scan:
        for path in iter_ofmx_files(args.scan):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
