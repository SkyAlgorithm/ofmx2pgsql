# ofmx2pgsql

Lightweight importer for OpenFlightMaps OFMX data into PostgreSQL/PostGIS. The goal is a small, auditable pipeline that parses OFMX XML, normalizes geometries, and loads core aviation features into a spatial schema.

## Status
Importer and schema are functional for the LK sample dataset. See `TODO.md` for remaining work and `PROGRESS.md` for a running log of changes.

## Setup
- `pip install -e .` installs the package and the `psycopg` dependency.
- `config/ofmx2pgsql.example.ini` shows the supported config keys.
- `Dockerfile` builds a container that downloads a snapshot and imports it into PostGIS.
- `docker-compose.yml` provides a PostGIS + importer stack for local testing.

## Repository Layout
- `ofmx_lk/` sample OFMX data and reference materials.
- `src/ofmx2pgsql/` application package (CLI, parsing, DB loaders).
- `sql/migrations/` PostGIS schema migrations.
- `config/` example configuration files.
- `tests/` minimal unit tests for parser and CLI.
- `TODO.md` roadmap and design checklist.
- `AGENTS.md` contributor guide for this repository.

## Current Capabilities
- Streaming XML parsing for OFMX datasets (Ahp, Rwy, Rdn, Ase, Dpn, Ndb/Vor/Dme).
- Airspace shapes parsed from OFM shape extension XML.
- PostGIS schema and import pipeline for airports, runways, runway ends, airspaces, navaids, and waypoints.
- CLI for scan/import/validate, with dry-run, verbose summaries, and JSON output.

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

## Docker Import
Build the image and run it with database credentials. The container downloads the snapshot URL and imports it.

```sh
docker build -t ofmx2pgsql .
docker run --rm \\
  -e PG_DSN=\"postgresql://user:pass@host:5432/db\" \\
  -e OFMX_URL=\"https://snapshots.openflightmaps.org/live/2513/ofmx/lkaa/latest/ofmx_lk.zip\" \\
  -e PG_SCHEMA=\"ofmx\" \\
  -e APPLY_MIGRATIONS=\"true\" \\
  ofmx2pgsql
```

## Docker Compose
Spin up a local PostGIS instance and run a one-shot import.

```sh
docker compose up --build --abort-on-container-exit
```

The compose stack builds a lightweight Postgres 18 + PostGIS image from `docker/postgis.Dockerfile` to support arm64 hosts.

## Data Notes
The sample data in `ofmx_lk/` is treated as reference input. Avoid editing these files unless intentionally updating fixtures.

Airspace records in the LK sample reuse `AseUid/@mid`, so `ofmx.airspaces.ofmx_id` is not unique. The schema uses a composite uniqueness constraint on `(ofmx_id, region, code_id, code_type, name)` to preserve distinct entries while keeping imports idempotent.
