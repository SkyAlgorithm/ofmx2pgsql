# Repository Guidelines

## Project Structure & Module Organization
- `TODO.md` captures the current roadmap for building the OFMX to PostGIS importer.
- `ofmx_lk/` contains sample OpenFlightMaps data and reference material.
  - `ofmx_lk/isolated/` includes individual OFMX artifacts (XML and extension files).
  - `ofmx_lk/embedded/` includes embedded OFMX data for integration testing.
- `ofmx_lk.zip` is a packaged copy of the data directory.

## Build, Test, and Development Commands
- No build or run commands are defined yet. When adding a CLI or tooling, document commands here (for example: `python -m ofmx2pgsql import ...` or `make test`).

## Coding Style & Naming Conventions
- No codebase conventions are established yet.
- When introducing code, prefer standard Python conventions (PEP 8, 4-space indentation) and descriptive module names (for example: `parser.py`, `db_writer.py`).
- If you add formatting or linting tools (for example: `ruff`, `black`), document the exact command and configuration paths.

## Testing Guidelines
- No automated tests are present. If you add tests, include:
  - The test framework and how to run it (for example: `pytest`).
  - Naming patterns (for example: `test_*.py`).
  - Any required sample data (point to `ofmx_lk/`).

## Commit & Pull Request Guidelines
- This repository is not currently a Git repo, so commit history is unavailable.
- If you initialize Git, use clear, imperative commit subjects (for example: `Add OFMX XML parser`) and include concise PR descriptions with the data sources and validation steps used.

## Data Handling Notes
- Treat `ofmx_lk/` as reference input data; avoid editing these files unless intentionally updating fixtures.
- If adding new sample datasets, store them alongside existing fixtures and keep filenames descriptive.
