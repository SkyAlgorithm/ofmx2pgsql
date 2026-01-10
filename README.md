# ofmx2pgsql

Lightweight importer for OpenFlightMaps OFMX data into PostgreSQL/PostGIS. The goal is a small, auditable pipeline that parses OFMX XML, normalizes geometries, and loads core aviation features into a spatial schema.

## Status
Early planning and data collection. See `TODO.md` for the build roadmap and `PROGRESS.md` for a running log of what exists today.

## Setup
- `pip install -e .` installs the package and the `psycopg` dependency.
- `config/ofmx2pgsql.example.ini` shows the supported config keys.

## Repository Layout
- `ofmx_lk/` sample OFMX data and reference materials.
- `src/ofmx2pgsql/` application package (CLI, parsing, DB loaders).
- `sql/migrations/` PostGIS schema migrations.
- `config/` example configuration files.
- `tests/` test suite (to be added).
- `TODO.md` roadmap and design checklist.
- `AGENTS.md` contributor guide for this repository.

## Planned Capabilities
- Streaming XML parsing for OFMX datasets.
- Geometry normalization (points and polygons initially).
- PostGIS schema for airports, runways, airspaces, navaids, and waypoints.
- CLI for imports, dry runs, and logging.
- Schema aligned to the LK sample entities (Ahp, Rwy, Rdn, Ase/Abd, Dpn, Ndb/Vor/Dme).

## Development Commands
- `python -m unittest discover -s tests` runs the minimal CLI smoke tests in `tests/`.
- `python -m ofmx2pgsql --help` verifies the CLI entry point is wired.
- `python -m ofmx2pgsql scan ofmx_lk/isolated` lists sample `.ofmx` files.
- `python -m ofmx2pgsql scan ofmx_lk/isolated --schema ofmx` prints a schema label before the list.
- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --schema ofmx --ofmx ofmx_lk/isolated/ofmx_lk.ofmx --shapes ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml --apply-migrations --verbose` loads the sample dataset.
- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --ofmx ofmx_lk/isolated/ofmx_lk.ofmx --shapes ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml --dry-run --verbose` parses without writing to the database.
- `python -m ofmx2pgsql validate --dsn \"postgresql://...\" --schema ofmx --ofmx ofmx_lk/isolated/ofmx_lk.ofmx --shapes ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml` compares parsed counts with stored counts.
- `python -m ofmx2pgsql validate --dsn \"postgresql://...\" --ofmx ofmx_lk/isolated/ofmx_lk.ofmx --output-json` emits validation output as JSON.
- `python -m ofmx2pgsql import --config config/ofmx2pgsql.example.ini --dry-run --verbose` uses config values with CLI overrides.
- `python -m ofmx2pgsql validate --config config/ofmx2pgsql.example.ini --output-json` uses config defaults with JSON output.

## Data Notes
The sample data in `ofmx_lk/` is treated as reference input. Avoid editing these files unless intentionally updating fixtures.

Airspace records in the LK sample reuse `AseUid/@mid`, so `ofmx.airspaces.ofmx_id` is not unique. The schema uses a composite uniqueness constraint on `(ofmx_id, region, code_id, code_type, name)` to preserve distinct entries while keeping imports idempotent.
