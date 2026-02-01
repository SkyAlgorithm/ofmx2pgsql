"""Command-line interface entry point."""

from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path

from .db import import_dataset, validate_dataset
from .parser import iter_ofmx_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ofmx2pgsql",
        description="Import OpenFlightMaps OFMX data into PostGIS.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="INI config file (section: [ofmx2pgsql]).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a file or directory for .ofmx files and list matches.",
    )
    scan_parser.add_argument("path", type=Path, metavar="PATH")
    scan_parser.add_argument(
        "--schema",
        help="Optional schema label to include in scan output.",
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import OFMX or ARINC data into PostGIS.",
    )
    import_parser.add_argument("--dsn", help="PostgreSQL DSN string.")
    import_source = import_parser.add_mutually_exclusive_group()
    import_source.add_argument(
        "--ofmx",
        type=Path,
        metavar="PATH",
        help="Path to an OFMX snapshot XML file.",
    )
    import_source.add_argument(
        "--arinc",
        type=Path,
        metavar="PATH",
        help="Path to an ARINC 424 .pc file or a ZIP containing it.",
    )
    import_parser.add_argument(
        "--shapes",
        type=Path,
        metavar="PATH",
        help="Optional OFM shape extension XML file for airspace polygons.",
    )
    import_parser.add_argument(
        "--openair",
        type=Path,
        metavar="PATH",
        help="Optional OpenAIR file or ZIP with airspace polygons (used with ARINC).",
    )
    import_parser.add_argument(
        "--apply-migrations",
        action="store_true",
        help="Apply the bundled schema migration before import.",
    )
    import_parser.add_argument(
        "--schema",
        help="Target Postgres schema (default: ofmx).",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and summarize without writing to the database.",
    )
    import_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print summary information during import.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Compare parsed counts with database row counts.",
    )
    validate_parser.add_argument("--dsn", help="PostgreSQL DSN string.")
    validate_source = validate_parser.add_mutually_exclusive_group()
    validate_source.add_argument(
        "--ofmx",
        type=Path,
        metavar="PATH",
        help="Path to an OFMX snapshot XML file.",
    )
    validate_source.add_argument(
        "--arinc",
        type=Path,
        metavar="PATH",
        help="Path to an ARINC 424 .pc file or a ZIP containing it.",
    )
    validate_parser.add_argument(
        "--shapes",
        type=Path,
        metavar="PATH",
        help="Optional OFM shape extension XML file for airspace polygons.",
    )
    validate_parser.add_argument(
        "--apply-migrations",
        action="store_true",
        help="Apply the bundled schema migration before validation.",
    )
    validate_parser.add_argument(
        "--schema",
        help="Target Postgres schema (default: ofmx).",
    )
    validate_parser.add_argument(
        "--output-json",
        action="store_true",
        help="Emit validation output as JSON.",
    )
    validate_parser.add_argument(
        "--filter-source",
        help="Restrict validation counts to rows with matching source.",
    )
    validate_parser.add_argument(
        "--filter-cycle",
        help="Restrict validation counts to rows with matching cycle.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scan":
        if args.schema:
            print(f"schema={args.schema}")
        for path in iter_ofmx_files(args.path):
            print(path)
        return 0
    if args.command == "import":
        _apply_config(args)
        _finalize_schema(args)
        _require_import_args(parser, args)
        source_path, source_format = _resolve_source(parser, args)
        import_dataset(
            dsn=args.dsn,
            source_path=source_path,
            shapes_path=args.shapes if source_format == "ofmx" else None,
            openair_path=args.openair if source_format == "arinc" else None,
            source_format=source_format,
            apply_migrations=args.apply_migrations,
            dry_run=args.dry_run,
            verbose=args.verbose,
            schema=args.schema,
        )
        return 0
    if args.command == "validate":
        _apply_config(args)
        _finalize_schema(args)
        _require_import_args(parser, args)
        source_path, source_format = _resolve_source(parser, args)
        result = validate_dataset(
            dsn=args.dsn,
            source_path=source_path,
            shapes_path=args.shapes if source_format == "ofmx" else None,
            source_format=source_format,
            filter_source=args.filter_source,
            filter_cycle=args.filter_cycle,
            apply_migrations=args.apply_migrations,
            schema=args.schema,
        )
        parsed = result["parsed"]
        stored = result["stored"]
        all_ok = True
        status: dict[str, bool] = {}
        for key in sorted(parsed.keys()):
            if key not in stored:
                continue
            ok = parsed[key] == stored[key]
            status[key] = ok
            all_ok = all_ok and ok
        if args.output_json:
            payload = {
                "parsed": parsed,
                "stored": stored,
                "match": status,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("Validation summary")
            for key in sorted(parsed.keys()):
                if key not in stored:
                    continue
                ok = status[key]
                state = "OK" if ok else "MISMATCH"
                print(f"{key}: parsed={parsed[key]} stored={stored[key]} [{state}]")
            if "airspace_shapes" in parsed and parsed["airspace_shapes"] > 0:
                print(f"airspace_shapes (parsed only): {parsed['airspace_shapes']}")
        return 0 if all_ok else 1
    return 0


def _apply_config(args: argparse.Namespace) -> None:
    if not args.config:
        return
    config = configparser.ConfigParser()
    config.read(args.config)
    section = config["ofmx2pgsql"] if "ofmx2pgsql" in config else None
    if section is None:
        return
    if getattr(args, "dsn", None) is None and "dsn" in section:
        args.dsn = section.get("dsn")
    if getattr(args, "ofmx", None) is None and "ofmx" in section:
        args.ofmx = Path(section.get("ofmx"))
    if getattr(args, "arinc", None) is None and "arinc" in section:
        args.arinc = Path(section.get("arinc"))
    if getattr(args, "shapes", None) is None and "shapes" in section:
        args.shapes = Path(section.get("shapes"))
    if getattr(args, "openair", None) is None and "openair" in section:
        args.openair = Path(section.get("openair"))
    if getattr(args, "apply_migrations", None) is False and "apply_migrations" in section:
        args.apply_migrations = section.getboolean("apply_migrations")
    if getattr(args, "dry_run", None) is False and "dry_run" in section:
        args.dry_run = section.getboolean("dry_run")
    if getattr(args, "verbose", None) is False and "verbose" in section:
        args.verbose = section.getboolean("verbose")
    if getattr(args, "schema", None) is None and "schema" in section:
        args.schema = section.get("schema")
    if getattr(args, "output_json", None) is False and "output_json" in section:
        args.output_json = section.getboolean("output_json")
    if getattr(args, "filter_source", None) is None and "filter_source" in section:
        args.filter_source = section.get("filter_source")
    if getattr(args, "filter_cycle", None) is None and "filter_cycle" in section:
        args.filter_cycle = section.get("filter_cycle")


def _finalize_schema(args: argparse.Namespace) -> None:
    if getattr(args, "schema", None) is None:
        args.schema = "ofmx"


def _require_import_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    missing = []
    if not getattr(args, "dsn", None):
        missing.append("--dsn")
    if not getattr(args, "ofmx", None) and not getattr(args, "arinc", None):
        missing.append("--ofmx/--arinc")
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")


def _resolve_source(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> tuple[Path, str]:
    if getattr(args, "ofmx", None) and getattr(args, "arinc", None):
        parser.error("Use only one of --ofmx or --arinc.")
    if getattr(args, "arinc", None):
        return args.arinc, "arinc"
    if getattr(args, "ofmx", None):
        return args.ofmx, "ofmx"
    parser.error("Missing required arguments: --ofmx or --arinc.")
    raise RuntimeError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
