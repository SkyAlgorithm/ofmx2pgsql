-- Baseline schema for OFMX imports (aligned with the LK sample dataset)

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS ofmx;

CREATE TABLE IF NOT EXISTS ofmx.airports (
    id BIGSERIAL PRIMARY KEY,
    ofmx_id TEXT UNIQUE NOT NULL,
    region TEXT,
    code_id TEXT,
    code_icao TEXT,
    code_gps TEXT,
    code_type TEXT,
    name TEXT,
    city TEXT,
    elevation INTEGER,
    elevation_uom TEXT,
    mag_var NUMERIC(6, 2),
    mag_var_year INTEGER,
    transition_alt INTEGER,
    transition_alt_uom TEXT,
    remarks TEXT,
    source TEXT,
    cycle TEXT,
    valid_from DATE,
    valid_to DATE,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS ofmx.runways (
    id BIGSERIAL PRIMARY KEY,
    ofmx_id TEXT UNIQUE NOT NULL,
    airport_ofmx_id TEXT REFERENCES ofmx.airports(ofmx_id),
    designator TEXT,
    length INTEGER,
    width INTEGER,
    uom_dim_rwy TEXT,
    surface TEXT,
    preparation TEXT,
    pcn_note TEXT,
    strip_length INTEGER,
    strip_width INTEGER,
    uom_dim_strip TEXT,
    source TEXT,
    cycle TEXT,
    valid_from DATE,
    valid_to DATE,
    geom geometry(LineString, 4326)
);

CREATE TABLE IF NOT EXISTS ofmx.runway_ends (
    id BIGSERIAL PRIMARY KEY,
    ofmx_id TEXT UNIQUE NOT NULL,
    runway_ofmx_id TEXT REFERENCES ofmx.runways(ofmx_id),
    airport_ofmx_id TEXT REFERENCES ofmx.airports(ofmx_id),
    designator TEXT,
    true_bearing NUMERIC(6, 2),
    mag_bearing NUMERIC(6, 2),
    source TEXT,
    cycle TEXT,
    valid_from DATE,
    valid_to DATE,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS ofmx.airspaces (
    id BIGSERIAL PRIMARY KEY,
    ofmx_id TEXT NOT NULL,
    region TEXT,
    code_id TEXT,
    code_type TEXT,
    name TEXT,
    name_alt TEXT,
    airspace_class TEXT,
    upper_ref TEXT,
    upper_value INTEGER,
    upper_uom TEXT,
    lower_ref TEXT,
    lower_value INTEGER,
    lower_uom TEXT,
    remarks TEXT,
    source TEXT,
    cycle TEXT,
    valid_from DATE,
    valid_to DATE,
    geom geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS ofmx.navaids (
    id BIGSERIAL PRIMARY KEY,
    ofmx_id TEXT UNIQUE NOT NULL,
    region TEXT,
    code_id TEXT,
    name TEXT,
    navaid_type TEXT,
    code_type TEXT,
    frequency NUMERIC(10, 3),
    frequency_uom TEXT,
    channel TEXT,
    ghost_frequency NUMERIC(10, 3),
    elevation INTEGER,
    elevation_uom TEXT,
    mag_var NUMERIC(6, 2),
    datum TEXT,
    associated_vor_ofmx_id TEXT REFERENCES ofmx.navaids(ofmx_id),
    source TEXT,
    cycle TEXT,
    valid_from DATE,
    valid_to DATE,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS ofmx.waypoints (
    id BIGSERIAL PRIMARY KEY,
    ofmx_id TEXT UNIQUE NOT NULL,
    region TEXT,
    code_id TEXT,
    name TEXT,
    point_type TEXT,
    source TEXT,
    cycle TEXT,
    valid_from DATE,
    valid_to DATE,
    geom geometry(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS airports_geom_gist ON ofmx.airports USING GIST (geom);
CREATE INDEX IF NOT EXISTS runways_geom_gist ON ofmx.runways USING GIST (geom);
CREATE INDEX IF NOT EXISTS runway_ends_geom_gist ON ofmx.runway_ends USING GIST (geom);
CREATE INDEX IF NOT EXISTS airspaces_geom_gist ON ofmx.airspaces USING GIST (geom);
CREATE INDEX IF NOT EXISTS airspaces_ofmx_id_idx ON ofmx.airspaces (ofmx_id);
CREATE UNIQUE INDEX IF NOT EXISTS airspaces_uidx
    ON ofmx.airspaces (ofmx_id, region, code_id, code_type, name);
CREATE INDEX IF NOT EXISTS navaids_geom_gist ON ofmx.navaids USING GIST (geom);
CREATE INDEX IF NOT EXISTS waypoints_geom_gist ON ofmx.waypoints USING GIST (geom);
