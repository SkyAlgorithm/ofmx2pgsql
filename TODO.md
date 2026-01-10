# ofmx2pgsql – TODO List

Build a lightweight importer for OpenFlightMaps OFMX data into PostgreSQL/PostGIS.

---

## Phase -1 — Repository Setup

- [x] Add contributor guidelines (`AGENTS.md`)
- [x] Add project overview (`README.md`)
- [x] Add progress log (`PROGRESS.md`)
- [x] Add base ignore rules (`.gitignore`)

---

## Phase 0 — Scope & Principles

- [ ] Define non-goals
  - [ ] No rendering optimizations
  - [ ] No tile generation
  - [ ] No attempt to support all OFMX edge cases initially
- [ ] Decide target CRS
  - [ ] Use EPSG:4326 only
- [ ] Decide geometry fidelity
  - [ ] Points and polygons only (no arcs initially)
- [ ] Define vertical dimension handling
  - [ ] Store altitudes as attributes (`lower_ft`, `upper_ft`)
  - [ ] No 3D geometries in v1

---

## Phase 1 — Understand OFMX Structure

- [ ] Obtain OFMX XSD schema
- [ ] Identify top-level entities
  - [ ] Airports
  - [ ] Runways
  - [ ] RunwayEnds
  - [ ] Airspaces
  - [ ] Navaids
  - [ ] Waypoints
- [ ] Map ID relationships
  - [ ] Airport ↔ Runway
  - [ ] Runway ↔ RunwayEnd
- [ ] Identify coordinate representations
  - [ ] Lat/Lon formats
  - [ ] Polygon definitions
  - [ ] Circles / arcs
- [ ] Document mandatory vs optional fields

---

## Phase 2 — Define PostGIS Schema

- [ ] Design core tables
  - [ ] airports
  - [ ] runways
  - [ ] runway_ends
  - [ ] airspaces
  - [ ] navaids
  - [ ] waypoints
- [ ] Define primary keys
- [ ] Store OFMX source IDs
- [ ] Define foreign keys
- [ ] Define geometry columns
  - [ ] POINT for airports, navaids, waypoints
  - [ ] POLYGON / MULTIPOLYGON for airspaces
- [ ] Add metadata fields
  - [ ] source
  - [ ] cycle
  - [ ] valid_from
  - [ ] valid_to
- [ ] Create spatial indexes (GIST)

---

## Phase 3 — Project Skeleton

- [x] Create repository `ofmx2pgsql`
- [x] Choose language
  - [x] Python
- [ ] Setup virtual environment
- [x] Setup CLI framework (`argparse` or `typer`)
- [x] Define project structure

---

## Phase 4 — XML Parsing Layer

- [x] Add parser module scaffold
- [ ] Implement streaming XML parser (`lxml.iterparse`)
- [ ] Implement entity parsers
- [ ] Normalize coordinates to decimal degrees
- [ ] Preserve OFMX IDs

---

## Phase 5 — Geometry Construction

- [ ] Convert coordinates to Shapely geometries
- [ ] Validate geometries
- [ ] Parse altitude limits

---

## Phase 6 — Database Writer

- [ ] Implement database connection
- [ ] Implement bulk inserts
- [ ] Implement idempotent loads

---

## Phase 7 — CLI Features

- [ ] Import command
- [ ] Schema selection
- [ ] Dry run
- [ ] Verbose logging

---

## Phase 8 — Validation & QA

- [ ] Compare counts with source
- [ ] Visual inspection in QGIS

---

## Phase 9 — Documentation

- [ ] README
- [ ] Example config
