"""Database import utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from . import parser

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
    ofmx_path: Path,
    shapes_path: Path | None = None,
    apply_migrations: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    schema: str = "ofmx",
) -> dict[str, int]:
    """Import an OFMX snapshot into PostGIS."""

    if dry_run:
        counts = summarize_dataset(ofmx_path, shapes_path)
        if verbose:
            _print_counts("Dry run summary", counts)
        return counts

    _ensure_driver()
    schema = _validate_schema(schema)
    with psycopg.connect(dsn) as conn:
        conn.execute(f"SET search_path = {schema}, public")
        if apply_migrations:
            apply_schema_migration(conn, schema=schema)
        counts = {
            "airports": _load_airports(conn, ofmx_path, schema),
            "runways": _load_runways(conn, ofmx_path, schema),
            "runway_ends": _load_runway_ends(conn, ofmx_path, schema),
            "airspaces": _load_airspaces(conn, ofmx_path, shapes_path, schema),
            "navaids": _load_navaids(conn, ofmx_path, schema),
            "waypoints": _load_waypoints(conn, ofmx_path, schema),
        }
        if verbose:
            _print_counts("Import summary", counts)
        return counts


def validate_dataset(
    *,
    dsn: str,
    ofmx_path: Path,
    shapes_path: Path | None = None,
    apply_migrations: bool = False,
    schema: str = "ofmx",
) -> dict[str, dict[str, int]]:
    """Compare parsed counts with database counts."""

    _ensure_driver()
    schema = _validate_schema(schema)
    with psycopg.connect(dsn) as conn:
        conn.execute(f"SET search_path = {schema}, public")
        if apply_migrations:
            apply_schema_migration(conn, schema=schema)
        parsed = summarize_dataset(ofmx_path, shapes_path)
        stored = _fetch_table_counts(conn, schema)
    return {"parsed": parsed, "stored": stored}


def apply_schema_migration(conn: "psycopg.Connection", *, schema: str = "ofmx") -> None:
    migration_path = Path(__file__).resolve().parents[2] / "sql" / "migrations" / "001_init.sql"
    sql = migration_path.read_text(encoding="utf-8")
    sql = sql.replace("CREATE SCHEMA IF NOT EXISTS ofmx;", f"CREATE SCHEMA IF NOT EXISTS {schema};")
    sql = sql.replace("ofmx.", f"{schema}.")
    conn.execute(sql)


def _load_airports(conn: "psycopg.Connection", ofmx_path: Path, schema: str) -> int:
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
            airport.longitude,
            airport.latitude,
        )
        for airport in parser.iter_airports(ofmx_path)
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
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
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
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_runways(conn: "psycopg.Connection", ofmx_path: Path, schema: str) -> int:
    runway_endpoints = _collect_runway_endpoints(ofmx_path)
    rows = []
    for runway in parser.iter_runways(ofmx_path):
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
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
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
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_runway_ends(conn: "psycopg.Connection", ofmx_path: Path, schema: str) -> int:
    rows = [
        (
            end.ofmx_id,
            end.runway_ofmx_id,
            end.airport_ofmx_id,
            end.designator,
            end.true_bearing,
            end.mag_bearing,
            end.longitude,
            end.latitude,
        )
        for end in parser.iter_runway_ends(ofmx_path)
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
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            runway_ofmx_id = EXCLUDED.runway_ofmx_id,
            airport_ofmx_id = EXCLUDED.airport_ofmx_id,
            designator = EXCLUDED.designator,
            true_bearing = EXCLUDED.true_bearing,
            mag_bearing = EXCLUDED.mag_bearing,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_airspaces(
    conn: "psycopg.Connection",
    ofmx_path: Path,
    shapes_path: Path | None,
    schema: str,
) -> int:
    shapes = _collect_airspace_shapes(shapes_path) if shapes_path else {}
    rows = []
    for airspace in parser.iter_airspaces(ofmx_path):
        shape = shapes.get(airspace.ofmx_id)
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
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
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
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_navaids(conn: "psycopg.Connection", ofmx_path: Path, schema: str) -> int:
    rows = [
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
            nav.longitude,
            nav.latitude,
        )
        for nav in parser.iter_navaids(ofmx_path)
    ]
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
            geom
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
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
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _load_waypoints(conn: "psycopg.Connection", ofmx_path: Path, schema: str) -> int:
    rows = [
        (
            point.ofmx_id,
            point.region,
            point.code_id,
            point.name,
            point.point_type,
            point.longitude,
            point.latitude,
        )
        for point in parser.iter_waypoints(ofmx_path)
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
            geom
        ) VALUES (
            %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (ofmx_id) DO UPDATE SET
            region = EXCLUDED.region,
            code_id = EXCLUDED.code_id,
            name = EXCLUDED.name,
            point_type = EXCLUDED.point_type,
            geom = EXCLUDED.geom
        """,
        rows,
    )
    return len(rows)


def _collect_runway_endpoints(ofmx_path: Path) -> Mapping[str, list[tuple[float, float]]]:
    endpoints: dict[str, list[tuple[float, float]]] = {}
    for end in parser.iter_runway_ends(ofmx_path):
        if end.longitude is None or end.latitude is None:
            continue
        endpoints.setdefault(end.runway_ofmx_id or "", []).append((end.longitude, end.latitude))
    return endpoints


def _collect_airspace_shapes(path: Path | None) -> Mapping[str, list[tuple[float, float]]]:
    if path is None:
        return {}
    shapes: dict[str, list[tuple[float, float]]] = {}
    for shape in parser.iter_airspace_shapes(path):
        shapes[shape.ofmx_id] = shape.positions
    return shapes


def summarize_dataset(ofmx_path: Path, shapes_path: Path | None) -> dict[str, int]:
    return {
        "airports": sum(1 for _ in parser.iter_airports(ofmx_path)),
        "runways": sum(1 for _ in parser.iter_runways(ofmx_path)),
        "runway_ends": sum(1 for _ in parser.iter_runway_ends(ofmx_path)),
        "airspaces": sum(1 for _ in parser.iter_airspaces(ofmx_path)),
        "navaids": sum(1 for _ in parser.iter_navaids(ofmx_path)),
        "waypoints": sum(1 for _ in parser.iter_waypoints(ofmx_path)),
        "airspace_shapes": (
            sum(1 for _ in parser.iter_airspace_shapes(shapes_path))
            if shapes_path
            else 0
        ),
    }


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


def _fetch_table_counts(conn: "psycopg.Connection", schema: str) -> dict[str, int]:
    tables = {
        "airports": f"{schema}.airports",
        "runways": f"{schema}.runways",
        "runway_ends": f"{schema}.runway_ends",
        "airspaces": f"{schema}.airspaces",
        "navaids": f"{schema}.navaids",
        "waypoints": f"{schema}.waypoints",
    }
    counts: dict[str, int] = {}
    for key, table in tables.items():
        counts[key] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return counts


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
