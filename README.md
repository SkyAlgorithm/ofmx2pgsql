# ofmx2pgsql

Lightweight importer for OpenFlightMaps OFMX data into PostgreSQL/PostGIS. The goal is a small, auditable pipeline that parses OFMX XML, normalizes geometries, and loads core aviation features into a spatial schema.

## Status
Early planning and data collection. See `TODO.md` for the build roadmap and `PROGRESS.md` for a running log of what exists today.

## Repository Layout
- `ofmx_lk/` sample OFMX data and reference materials.
- `src/ofmx2pgsql/` application package (CLI, parsing, DB loaders).
- `tests/` test suite (to be added).
- `TODO.md` roadmap and design checklist.
- `AGENTS.md` contributor guide for this repository.

## Planned Capabilities
- Streaming XML parsing for OFMX datasets.
- Geometry normalization (points and polygons initially).
- PostGIS schema for airports, runways, airspaces, navaids, and waypoints.
- CLI for imports, dry runs, and logging.

## Development Commands
- `python -m unittest discover -s tests` runs the minimal CLI smoke tests in `tests/`.
- `python -m ofmx2pgsql --help` verifies the CLI entry point is wired.
- `python -m ofmx2pgsql --scan ofmx_lk/isolated` lists sample `.ofmx` files.

## Data Notes
The sample data in `ofmx_lk/` is treated as reference input. Avoid editing these files unless intentionally updating fixtures.
