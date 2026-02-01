# ofmx2pgsql

[![CI](https://github.com/SkyAlgorithm/ofmx2pgsql/actions/workflows/ci.yml/badge.svg)](https://github.com/SkyAlgorithm/ofmx2pgsql/actions/workflows/ci.yml)

An open-source SkyAlgorithm project.

Minimal OFMX → PostGIS importer for OpenFlightMaps snapshots.

Lightweight importer for OpenFlightMaps OFMX data into PostgreSQL/PostGIS. The goal is a small, auditable pipeline that parses OFMX XML, normalizes geometries, and loads core aviation features into a spatial schema.

## Status
Importer and schema are functional for LKAA and ED snapshots. Data is fetched on demand and CI validates parser behavior and the Docker import path.

## Design Principles
- Keep the pipeline small and auditable.
- Favor explicit schemas over implicit inference.
- Make data fetching and imports reproducible.

## Setup
- `pip install -e .` installs the package and the `psycopg` dependency.
- `config/ofmx2pgsql.example.ini` shows the supported config keys.
- `Dockerfile` builds a container that downloads a snapshot and imports it into PostGIS.
- `scripts/fetch_ofmx.sh` downloads and extracts a snapshot locally for CLI testing.

## Repository Layout
- `src/ofmx2pgsql/` application package (CLI, parsing, DB loaders).
- `sql/migrations/` PostGIS schema migrations.
- `config/` example configuration files.
- `tests/` minimal unit tests for parser and CLI.
- `scripts/` helper scripts for fetching data and container workflows.

## Current Capabilities
- Streaming XML parsing for OFMX datasets (Ahp, Rwy, Rdn, Ase, Dpn, Ndb/Vor/Dme).
- ARINC 424 parsing for airports, runways, runway ends, airspaces, navaids, and waypoints.
- Airspace shapes parsed from OFM shape extension XML.
- ARINC airspace imports load metadata only (no polygon geometry).
- OpenAIR parsing for ARINC airspace polygons when supplied via `--openair`.
- PostGIS schema and import pipeline for airports, runways, runway ends, airspaces, navaids, and waypoints.
- CLI for scan/import/validate, with dry-run, verbose summaries, and JSON output.

## Development Commands
- `python -m unittest discover -s tests` runs the minimal CLI smoke tests in `tests/`.
- `python -m ofmx2pgsql --help` verifies the CLI entry point is wired.
- `scripts/fetch_ofmx.sh` downloads and extracts the LK snapshot into `data/`.
- `python -m ofmx2pgsql scan data/ofmx_lk/isolated` lists `.ofmx` files.
- `python -m ofmx2pgsql scan data/ofmx_lk/isolated --schema ofmx` prints a schema label before the list.
- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --schema ofmx --ofmx data/ofmx_lk/isolated/ofmx_lk.ofmx --shapes data/ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml --apply-migrations --verbose` loads the sample dataset.
- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --ofmx data/ofmx_lk/isolated/ofmx_lk.ofmx --shapes data/ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml --dry-run --verbose` parses without writing to the database.
- `python -m ofmx2pgsql validate --dsn \"postgresql://...\" --schema ofmx --ofmx data/ofmx_lk/isolated/ofmx_lk.ofmx --shapes data/ofmx_lk/isolated/ofmx_lk_ofmShapeExtension.xml` compares parsed counts with stored counts.
- `python -m ofmx2pgsql validate --dsn \"postgresql://...\" --ofmx data/ofmx_lk/isolated/ofmx_lk.ofmx --output-json` emits validation output as JSON.
- `python -m ofmx2pgsql import --config config/ofmx2pgsql.example.ini --dry-run --verbose` uses config values with CLI overrides.
- `python -m ofmx2pgsql validate --config config/ofmx2pgsql.example.ini --output-json` uses config defaults with JSON output.

## Docker Import
Build the image and run it with database credentials. The container downloads the snapshot URL and imports it.

```sh
docker build -t ofmx2pgsql .
docker run --rm \
  -e PG_DSN="postgresql://user:pass@host:5432/db" \
  -e OFMX_URL="https://snapshots.openflightmaps.org/live/2513/ofmx/lkaa/latest/ofmx_lk.zip" \
  -e PG_SCHEMA="ofmx" \
  -e APPLY_MIGRATIONS="true" \
  ofmx2pgsql
```

## OFMX Data Notes
The LK sample data is fetched on demand into `data/ofmx_lk/` via `scripts/fetch_ofmx.sh` and is ignored by git.

Airspace records in the LK sample reuse `AseUid/@mid`, so `ofmx.airspaces.ofmx_id` is not unique. The schema uses a composite uniqueness constraint on `(ofmx_id, region, code_id, code_type, name)` to preserve distinct entries while keeping imports idempotent.

## ARINC / OpenAIR
OpenFlightMaps does not publish OFMX for Switzerland (LS). Use ARINC 424 plus OpenAIR shapes for this region.

ARINC + OpenAIR (Switzerland) import with the Docker image:

```sh
docker run --rm \
  -e PG_DSN="postgresql://user:pass@host:5432/db" \
  -e ARINC_URL="https://snapshots.openflightmaps.org/live/2601/arinc424/lsas/latest/arinc_ls.zip" \
  -e OPENAIR_URL="https://snapshots.openflightmaps.org/live/2601/openair/lsas/latest/openair_ls.zip" \
  -e PG_SCHEMA="ofmx" \
  -e APPLY_MIGRATIONS="true" \
  ofmx2pgsql
```

ARINC command-line examples:

- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --arinc data/arinc_ls/isolated/arinc_ls.pc --apply-migrations --verbose` imports ARINC 424 data into the same tables.
- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --arinc /path/to/arinc_ls.zip --dry-run --verbose` parses a ZIP-contained ARINC dataset without writing to the database.
- `python -m ofmx2pgsql import --dsn \"postgresql://...\" --arinc /path/to/arinc_ls.zip --openair /path/to/openair_ls.zip --apply-migrations --verbose` enriches ARINC airspaces with OpenAIR polygons.
- `python -m ofmx2pgsql validate --dsn \"postgresql://...\" --arinc /path/to/arinc_ls.zip --filter-source arinc --filter-cycle 2601 --output-json` validates only rows imported from ARINC cycle 2601.


### Validation Notes
Validation compares parsed counts to database row counts in the selected schema. If you import multiple regions into the same schema, raw totals won't match a single file. For ARINC imports we tag rows with:

- `source='arinc'`
- `cycle='2601'` (or whatever cycle is in the ARINC file)

Use those tags to validate only the rows from a specific import:

```sh
python -m ofmx2pgsql validate \
  --dsn "postgresql://..." \
  --arinc /path/to/arinc_ls.zip \
  --filter-source arinc \
  --filter-cycle 2601 \
  --output-json
```



## Development Notes
See `CONTRIBUTING.md` for workflow and style notes used by maintainers.

## Security
See `SECURITY.md` for reporting guidance.

## Roadmap
- Expand parser coverage for additional OFMX features (procedures, routes, obstacles).
- Add integration tests that validate full imports against a disposable PostGIS instance.

## License
MIT. See `LICENSE`.

## Data Sources
OFMX data is sourced from OpenFlightMaps snapshots. Review their terms and attribution requirements before redistribution.
