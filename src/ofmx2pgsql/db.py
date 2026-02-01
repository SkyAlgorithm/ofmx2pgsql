"""Database import utilities."""

from __future__ import annotations

from pathlib import Path
import importlib.resources as resources
from typing import Iterable, Mapping
import re
import unicodedata

from . import arinc, openair, parser

try:
    import psycopg
except ImportError as exc:  # pragma: no cover - runtime-only path
    psycopg = None
    _PSYCOPG_IMPORT_ERROR = exc
else:
    _PSYCOPG_IMPORT_ERROR = None


def import_dataset(
    *,
    dsn: str,
    source_path: Path,
    shapes_path: Path | None = None,
    openair_path: Path | None = None,
    source_format: str = "ofmx",
    apply_migrations: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    schema: str = "ofmx",
) -> dict[str, int]:
    """Import an OFMX or ARINC snapshot into PostGIS."""

    if dry_run:
        counts = summarize_dataset(source_path, shapes_path, source_format=source_format)
        if verbose:
            _print_counts("Dry run summary", counts)
        return counts

    _ensure_driver()
    schema = _validate_schema(schema)
    parser_module = _select_parser(source_format)
    source_label = _source_label(source_format)
    cycle = _source_cycle(source_format, source_path)
    with psycopg.connect(dsn) as conn:
        conn.execute(f"SET search_path = {schema}, public")
        if apply_migrations:
            apply_schema_migration(conn, schema=schema)
        counts = {
            "airports": _load_airports(conn, parser_module, source_path, schema, source_label, cycle),
            "runways": _load_runways(conn, parser_module, source_path, schema, source_label, cycle),
            "runway_ends": _load_runway_ends(
                conn, parser_module, source_path, schema, source_label, cycle
            ),
            "airspaces": _load_airspaces(
                conn,
                parser_module,
                source_path,
                shapes_path if source_format == "ofmx" else None,
                schema,
                source_label,
                cycle,
                openair_path if source_format == "arinc" else None,
            ),
            "navaids": _load_navaids(conn, parser_module, source_path, schema, source_label, cycle),
            "waypoints": _load_waypoints(
                conn, parser_module, source_path, schema, source_label, cycle
            ),
        }
        if verbose:
            _print_counts("Import summary", counts)
        return counts


def validate_dataset(
    *,
    dsn: str,
    source_path: Path,
    shapes_path: Path | None = None,
    source_format: str = "ofmx",
    filter_source: str | None = None,
    filter_cycle: str | None = None,
    apply_migrations: bool = False,
    schema: str = "ofmx",
) -> dict[str, dict[str, int]]:
    """Compare parsed counts with database counts."""

    _ensure_driver()
    schema = _validate_schema(schema)
    parser_module = _select_parser(source_format)
    with psycopg.connect(dsn) as conn:
        conn.execute(f"SET search_path = {schema}, public")
        if apply_migrations:
            apply_schema_migration(conn, schema=schema)
        parsed = summarize_dataset(source_path, shapes_path, source_format=source_format)
        stored = _fetch_table_counts(conn, schema, filter_source, filter_cycle)
    return {"parsed": parsed, "stored": stored}


def apply_schema_migration(conn: "psycopg.Connection", *, schema: str = "ofmx") -> None:
    migration_path = Path(__file__).resolve().parents[2] / "sql" / "migrations" / "001_init.sql"
    if migration_path.exists():
        sql = migration_path.read_text(encoding="utf-8")
    else:
        sql = resources.files("ofmx2pgsql.sql").joinpath("migrations/001_init.sql").read_text(
            encoding="utf-8"
        )
    sql = sql.replace("CREATE SCHEMA IF NOT EXISTS ofmx;", f"CREATE SCHEMA IF NOT EXISTS {schema};")
    sql = sql.replace("ofmx.", f"{schema}.")
    conn.execute(sql)


def _load_airports(
    conn: "psycopg.Connection",
    parser_module,
    source_path: Path,
    schema: str,
    source_label: str | None,
    cycle: str | None,
) -> int:
    rows = [
        (
            airport.ofmx_id,
            airport.region,
            airport.code_id,
            airport.code_icao,
            airport.code_gps,
            airport.code_type,
            airport.name,
            airport.city,
            airport.elevation,
            airport.elevation_uom,
            airport.mag_var,
            airport.mag_var_year,
            airport.transition_alt,
            airport.transition_alt_uom,
            airport.remarks,
            source_label,
            cycle,
            airport.longitude,
            airport.latitude,
        )
        for airport in parser_module.iter_airports(source_path)
    ]
    if not rows:
        return 0
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.airports (
            ofmx_id,
            region,
            code_id,
            code_icao,
            code_gps,
            code_type,
            name,
            city,
            elevation,
            elevation_uom,
            mag_var,
            mag_var_year,
            transition_alt,
            transition_alt_uom,
            remarks,
            source,
            cycle,
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            region = EXCLUDED.region,
            code_id = EXCLUDED.code_id,
            code_icao = EXCLUDED.code_icao,
            code_gps = EXCLUDED.code_gps,
            code_type = EXCLUDED.code_type,
            name = EXCLUDED.name,
            city = EXCLUDED.city,
            elevation = EXCLUDED.elevation,
            elevation_uom = EXCLUDED.elevation_uom,
            mag_var = EXCLUDED.mag_var,
            mag_var_year = EXCLUDED.mag_var_year,
            transition_alt = EXCLUDED.transition_alt,
            transition_alt_uom = EXCLUDED.transition_alt_uom,
            remarks = EXCLUDED.remarks,
            source = EXCLUDED.source,
            cycle = EXCLUDED.cycle,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_runways(
    conn: "psycopg.Connection",
    parser_module,
    source_path: Path,
    schema: str,
    source_label: str | None,
    cycle: str | None,
) -> int:
    runway_endpoints = _collect_runway_endpoints(parser_module, source_path)
    rows = []
    for runway in parser_module.iter_runways(source_path):
        geom = _line_wkt(runway_endpoints.get(runway.ofmx_id, []))
        rows.append(
            (
                runway.ofmx_id,
                runway.airport_ofmx_id,
                runway.designator,
                runway.length,
                runway.width,
                runway.uom_dim_rwy,
                runway.surface,
                runway.preparation,
                runway.pcn_note,
                runway.strip_length,
                runway.strip_width,
                runway.uom_dim_strip,
                source_label,
                cycle,
                geom,
                geom,
            )
        )
    if not rows:
        return 0
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.runways (
            ofmx_id,
            airport_ofmx_id,
            designator,
            length,
            width,
            uom_dim_rwy,
            surface,
            preparation,
            pcn_note,
            strip_length,
            strip_width,
            uom_dim_strip,
            source,
            cycle,
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            CASE WHEN %s::text IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s::text), 4326) END
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            airport_ofmx_id = EXCLUDED.airport_ofmx_id,
            designator = EXCLUDED.designator,
            length = EXCLUDED.length,
            width = EXCLUDED.width,
            uom_dim_rwy = EXCLUDED.uom_dim_rwy,
            surface = EXCLUDED.surface,
            preparation = EXCLUDED.preparation,
            pcn_note = EXCLUDED.pcn_note,
            strip_length = EXCLUDED.strip_length,
            strip_width = EXCLUDED.strip_width,
            uom_dim_strip = EXCLUDED.uom_dim_strip,
            source = EXCLUDED.source,
            cycle = EXCLUDED.cycle,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_runway_ends(
    conn: "psycopg.Connection",
    parser_module,
    source_path: Path,
    schema: str,
    source_label: str | None,
    cycle: str | None,
) -> int:
    rows = [
        (
            end.ofmx_id,
            end.runway_ofmx_id,
            end.airport_ofmx_id,
            end.designator,
            end.true_bearing,
            end.mag_bearing,
            source_label,
            cycle,
            end.longitude,
            end.latitude,
        )
        for end in parser_module.iter_runway_ends(source_path)
    ]
    if not rows:
        return 0
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.runway_ends (
            ofmx_id,
            runway_ofmx_id,
            airport_ofmx_id,
            designator,
            true_bearing,
            mag_bearing,
            source,
            cycle,
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            runway_ofmx_id = EXCLUDED.runway_ofmx_id,
            airport_ofmx_id = EXCLUDED.airport_ofmx_id,
            designator = EXCLUDED.designator,
            true_bearing = EXCLUDED.true_bearing,
            mag_bearing = EXCLUDED.mag_bearing,
            source = EXCLUDED.source,
            cycle = EXCLUDED.cycle,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_airspaces(
    conn: "psycopg.Connection",
    parser_module,
    source_path: Path,
    shapes_path: Path | None,
    schema: str,
    source_label: str | None,
    cycle: str | None,
    openair_path: Path | None,
) -> int:
    shapes = _collect_airspace_shapes(parser_module, shapes_path) if shapes_path else {}
    openair_shapes = _collect_openair_shapes(openair_path) if openair_path else {}
    rows = []
    for airspace in parser_module.iter_airspaces(source_path):
        shape = shapes.get(airspace.ofmx_id)
        if shape is None and openair_shapes:
            key = (_normalize_name(airspace.name), _normalize_class(airspace.airspace_class))
            shape = openair_shapes.get(key)
        polygon = _polygon_wkt(shape) if shape else None
        rows.append(
            (
                airspace.ofmx_id,
                airspace.region,
                airspace.code_id,
                airspace.code_type,
                airspace.name,
                airspace.name_alt,
                airspace.airspace_class,
                airspace.upper_ref,
                airspace.upper_value,
                airspace.upper_uom,
                airspace.lower_ref,
                airspace.lower_value,
                airspace.lower_uom,
                airspace.remarks,
                source_label,
                cycle,
                polygon,
                polygon,
            )
        )
    if not rows:
        return 0
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.airspaces (
            ofmx_id,
            region,
            code_id,
            code_type,
            name,
            name_alt,
            airspace_class,
            upper_ref,
            upper_value,
            upper_uom,
            lower_ref,
            lower_value,
            lower_uom,
            remarks,
            source,
            cycle,
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            CASE WHEN %s::text IS NULL THEN NULL ELSE ST_Multi(ST_SetSRID(ST_GeomFromText(%s::text), 4326)) END
        )
        ON CONFLICT (ofmx_id, region, code_id, code_type, name) DO UPDATE SET
            name = EXCLUDED.name,
            name_alt = EXCLUDED.name_alt,
            airspace_class = EXCLUDED.airspace_class,
            upper_ref = EXCLUDED.upper_ref,
            upper_value = EXCLUDED.upper_value,
            upper_uom = EXCLUDED.upper_uom,
            lower_ref = EXCLUDED.lower_ref,
            lower_value = EXCLUDED.lower_value,
            lower_uom = EXCLUDED.lower_uom,
            remarks = EXCLUDED.remarks,
            source = EXCLUDED.source,
            cycle = EXCLUDED.cycle,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_navaids(
    conn: "psycopg.Connection",
    parser_module,
    source_path: Path,
    schema: str,
    source_label: str | None,
    cycle: str | None,
) -> int:
    rows = []
    for nav in parser_module.iter_navaids(source_path):
        if nav.longitude is None or nav.latitude is None:
            continue
        rows.append(
            (
                nav.ofmx_id,
                nav.region,
                nav.code_id,
                nav.name,
                nav.navaid_type,
                nav.code_type,
                nav.frequency,
                nav.frequency_uom,
                nav.channel,
                nav.ghost_frequency,
                nav.elevation,
                nav.elevation_uom,
                nav.mag_var,
                nav.datum,
                nav.associated_vor_ofmx_id,
                source_label,
                cycle,
                nav.longitude,
                nav.latitude,
            )
        )
    if not rows:
        return 0
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.navaids (
            ofmx_id,
            region,
            code_id,
            name,
            navaid_type,
            code_type,
            frequency,
            frequency_uom,
            channel,
            ghost_frequency,
            elevation,
            elevation_uom,
            mag_var,
            datum,
            associated_vor_ofmx_id,
            source,
            cycle,
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            region = EXCLUDED.region,
            code_id = EXCLUDED.code_id,
            name = EXCLUDED.name,
            navaid_type = EXCLUDED.navaid_type,
            code_type = EXCLUDED.code_type,
            frequency = EXCLUDED.frequency,
            frequency_uom = EXCLUDED.frequency_uom,
            channel = EXCLUDED.channel,
            ghost_frequency = EXCLUDED.ghost_frequency,
            elevation = EXCLUDED.elevation,
            elevation_uom = EXCLUDED.elevation_uom,
            mag_var = EXCLUDED.mag_var,
            datum = EXCLUDED.datum,
            associated_vor_ofmx_id = EXCLUDED.associated_vor_ofmx_id,
            source = EXCLUDED.source,
            cycle = EXCLUDED.cycle,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_waypoints(
    conn: "psycopg.Connection",
    parser_module,
    source_path: Path,
    schema: str,
    source_label: str | None,
    cycle: str | None,
) -> int:
    rows = [
        (
            point.ofmx_id,
            point.region,
            point.code_id,
            point.name,
            point.point_type,
            source_label,
            cycle,
            point.longitude,
            point.latitude,
        )
        for point in parser_module.iter_waypoints(source_path)
    ]
    if not rows:
        return 0
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.waypoints (
            ofmx_id,
            region,
            code_id,
            name,
            point_type,
            source,
            cycle,
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            region = EXCLUDED.region,
            code_id = EXCLUDED.code_id,
            name = EXCLUDED.name,
            point_type = EXCLUDED.point_type,
            source = EXCLUDED.source,
            cycle = EXCLUDED.cycle,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _collect_runway_endpoints(
    parser_module, source_path: Path
) -> Mapping[str, list[tuple[float, float]]]:
    endpoints: dict[str, list[tuple[float, float]]] = {}
    for end in parser_module.iter_runway_ends(source_path):
        if end.longitude is None or end.latitude is None:
            continue
        endpoints.setdefault(end.runway_ofmx_id or "", []).append((end.longitude, end.latitude))
    return endpoints


def _collect_airspace_shapes(
    parser_module, path: Path | None
) -> Mapping[str, list[tuple[float, float]]]:
    if path is None:
        return {}
    shapes: dict[str, list[tuple[float, float]]] = {}
    for shape in parser_module.iter_airspace_shapes(path):
        shapes[shape.ofmx_id] = shape.positions
    return shapes


def _collect_openair_shapes(
    path: Path | None,
) -> Mapping[tuple[str, str | None], list[tuple[float, float]]]:
    if path is None:
        return {}
    return openair.build_shape_index(path)


def _normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = normalized.strip().upper().split()
    if tokens[:1] == ["R"] and len(tokens) > 1 and tokens[1].startswith("LS"):
        tokens = tokens[1:]
    while tokens and re.fullmatch(r"\d+\.\d+", tokens[-1]):
        tokens.pop()
    return " ".join(tokens)


def _normalize_class(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().upper() or None


def summarize_dataset(
    source_path: Path, shapes_path: Path | None, *, source_format: str = "ofmx"
) -> dict[str, int]:
    parser_module = _select_parser(source_format)
    if source_format == "arinc":
        return {
            "airports": _count_unique(parser_module.iter_airports(source_path)),
            "runways": _count_unique(parser_module.iter_runways(source_path)),
            "runway_ends": _count_unique(parser_module.iter_runway_ends(source_path)),
            "airspaces": _count_unique(parser_module.iter_airspaces(source_path)),
            "navaids": _count_unique(
                parser_module.iter_navaids(source_path),
                predicate=lambda nav: nav.longitude is not None and nav.latitude is not None,
            ),
            "waypoints": _count_unique(parser_module.iter_waypoints(source_path)),
            "airspace_shapes": 0,
        }
    return {
        "airports": sum(1 for _ in parser_module.iter_airports(source_path)),
        "runways": sum(1 for _ in parser_module.iter_runways(source_path)),
        "runway_ends": sum(1 for _ in parser_module.iter_runway_ends(source_path)),
        "airspaces": sum(1 for _ in parser_module.iter_airspaces(source_path)),
        "navaids": sum(1 for _ in parser_module.iter_navaids(source_path)),
        "waypoints": sum(1 for _ in parser_module.iter_waypoints(source_path)),
        "airspace_shapes": (
            sum(1 for _ in parser_module.iter_airspace_shapes(shapes_path))
            if shapes_path and source_format == "ofmx"
            else 0
        ),
    }


def _count_unique(records, predicate=None) -> int:
    seen: set[str] = set()
    for record in records:
        if predicate is not None and not predicate(record):
            continue
        seen.add(record.ofmx_id)
    return len(seen)


def _select_parser(source_format: str):
    if source_format == "arinc":
        return arinc
    return parser


def _source_label(source_format: str) -> str | None:
    if source_format == "arinc":
        return "arinc"
    return None


def _source_cycle(source_format: str, source_path: Path) -> str | None:
    if source_format == "arinc":
        return arinc.read_cycle(source_path)
    return None


def _line_wkt(points: Iterable[tuple[float, float]]) -> str | None:
    coords = list(points)
    if len(coords) < 2:
        return None
    parts = ", ".join(f"{lon} {lat}" for lon, lat in coords[:2])
    return f"LINESTRING({parts})"


def _polygon_wkt(points: Iterable[tuple[float, float]]) -> str | None:
    coords = list(points)
    if len(coords) < 3:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    parts = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"POLYGON(({parts}))"


def _fetch_table_counts(
    conn: "psycopg.Connection",
    schema: str,
    filter_source: str | None = None,
    filter_cycle: str | None = None,
) -> dict[str, int]:
    tables = {
        "airports": f"{schema}.airports",
        "runways": f"{schema}.runways",
        "runway_ends": f"{schema}.runway_ends",
        "airspaces": f"{schema}.airspaces",
        "navaids": f"{schema}.navaids",
        "waypoints": f"{schema}.waypoints",
    }
    where, params = _build_filter_clause(filter_source, filter_cycle)
    counts: dict[str, int] = {}
    for key, table in tables.items():
        query = f"SELECT COUNT(*) FROM {table}{where}"
        counts[key] = conn.execute(query, params).fetchone()[0]
    return counts


def _build_filter_clause(
    filter_source: str | None, filter_cycle: str | None
) -> tuple[str, tuple[object, ...]]:
    parts: list[str] = []
    params: list[object] = []
    if filter_source:
        parts.append("source = %s")
        params.append(filter_source)
    if filter_cycle:
        parts.append("cycle = %s")
        params.append(filter_cycle)
    if not parts:
        return "", ()
    return " WHERE " + " AND ".join(parts), tuple(params)


def _print_counts(title: str, counts: dict[str, int]) -> None:
    print(title)
    for key, value in counts.items():
        print(f"{key}: {value}")


def _executemany(conn: "psycopg.Connection", query: str, rows: list[tuple]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(query, rows)


def _ensure_driver() -> None:
    if psycopg is None:
        raise RuntimeError(
            "psycopg is required for database operations. Install with `pip install psycopg`."
        ) from _PSYCOPG_IMPORT_ERROR


def _validate_schema(schema: str) -> str:
    if not schema or not schema.replace("_", "").isalnum() or schema[0].isdigit():
        raise ValueError(f"Invalid schema name: {schema}")
    return schema
