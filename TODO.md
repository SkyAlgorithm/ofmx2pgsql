# ofmx2pgsql – TODO List

Focused, remaining work for the OFMX-to-PostGIS importer.

## Done (Milestones)
- Repository bootstrapped (docs, config, tests, schema, CLI).
- Parser and importer wired to LK sample data.
- Import validation and dry-run workflows implemented.
## Scope Decisions
- Confirm non-goals (no rendering, no tile generation, limited edge-case support).
- Lock CRS (EPSG:4326 only).
- Confirm geometry fidelity (points, lines, polygons; arcs handled only via extension).
- Decide altitude handling (attribute columns vs 3D geometries).

## OFMX Understanding
- Obtain and pin the OFMX XSD schema version used by the dataset.
- Document mandatory vs optional fields for Ahp/Rwy/Rdn/Ase/Dpn/Ndb/Vor/Dme.
- Clarify coordinate formats and arc/circle handling in core XML vs extensions.

## Parsing & Geometry
- Add geometry construction helpers (Shapely or raw WKT) for non-airspace shapes.
- Validate geometries (self-intersections, ring closure, SRID consistency).
- Parse altitude limits into numeric fields with normalized units.

## Database & Import
- Populate metadata fields (`source`, `cycle`, `valid_from`, `valid_to`) during import.
- Decide how to version or archive imports across cycles.

## Validation & QA
- Visual inspection in QGIS for a sample import.
- Add a lightweight regression dataset comparison (counts + spot checks).
