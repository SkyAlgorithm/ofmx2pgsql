"""ARINC 424 parsing utilities for OpenFlightMaps ARINC snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional
import io
import zipfile

from .parser import Airspace, AirspaceShape, Airport, Navaid, Runway, RunwayEnd, Waypoint


def read_cycle(path: Path) -> Optional[str]:
    """Return the cycle code from the first ARINC record, if present."""

    for line in _iter_lines(path):
        cycle = _strip(line[128:132])
        return cycle
    return None


def iter_airports(path: Path) -> Iterator[Airport]:
    """Yield airports from an ARINC 424 dataset."""

    airports: list[Airport] = []
    codes: set[str] = set()
    for line in _iter_lines(path):
        if not _is_section(line, "PA"):
            continue
        if line[21] != "0":
            continue
        icao = _strip(line[6:10])
        if not icao:
            continue
        codes.add(icao)
        ofmx_id = _airport_id(icao)
        code_id = icao
        airports.append(
            Airport(
                ofmx_id=ofmx_id,
                region=_strip(line[10:12]),
                code_id=code_id,
                code_icao=icao,
                code_gps=None,
                code_type=None,
                name=_strip(line[93:123]),
                city=None,
                elevation=_to_int(line[56:61]),
                elevation_uom="FT" if _strip(line[56:61]) else None,
                mag_var=_parse_mag_var(line[51:56]),
                mag_var_year=None,
                transition_alt=_to_int(line[70:75]),
                transition_alt_uom="FT" if _strip(line[70:75]) else None,
                remarks=None,
                latitude=_parse_lat(line[32:41]),
                longitude=_parse_lon(line[41:51]),
            )
        )
    runway_coords: dict[str, list[tuple[float, float]]] = {}
    for line in _iter_lines(path):
        if not _is_section(line, "PG"):
            continue
        if line[21] != "0":
            continue
        icao = _strip(line[6:10])
        if not icao or icao in codes:
            continue
        lat = _parse_lat(line[32:41])
        lon = _parse_lon(line[41:51])
        if lat is not None and lon is not None:
            runway_coords.setdefault(icao, []).append((lat, lon))
    for icao, coords in runway_coords.items():
        if icao in codes:
            continue
        codes.add(icao)
        if coords:
            lat = sum(point[0] for point in coords) / len(coords)
            lon = sum(point[1] for point in coords) / len(coords)
        else:
            lat = None
            lon = None
        airports.append(
            Airport(
                ofmx_id=_airport_id(icao),
                region=None,
                code_id=icao,
                code_icao=icao,
                code_gps=None,
                code_type=None,
                name=None,
                city=None,
                elevation=None,
                elevation_uom=None,
                mag_var=None,
                mag_var_year=None,
                transition_alt=None,
                transition_alt_uom=None,
                remarks=None,
                latitude=lat,
                longitude=lon,
            )
        )
    yield from airports


def iter_runways(path: Path) -> Iterator[Runway]:
    """Yield runways from an ARINC 424 dataset."""

    runways: dict[str, Runway] = {}
    for data in _iter_runway_end_data(path):
        runway = runways.get(data.runway_ofmx_id)
        if runway is None:
            runways[data.runway_ofmx_id] = Runway(
                ofmx_id=data.runway_ofmx_id,
                airport_ofmx_id=data.airport_ofmx_id,
                designator=data.pair_designator,
                length=data.length,
                width=data.width,
                uom_dim_rwy="FT" if data.length or data.width else None,
                surface=None,
                preparation=None,
                pcn_note=None,
                strip_length=None,
                strip_width=None,
                uom_dim_strip=None,
            )
        else:
            runways[data.runway_ofmx_id] = _merge_runways(runway, data)
    yield from runways.values()


def iter_runway_ends(path: Path) -> Iterator[RunwayEnd]:
    """Yield runway ends from an ARINC 424 dataset."""

    for data in _iter_runway_end_data(path):
        yield RunwayEnd(
            ofmx_id=data.runway_end_id,
            runway_ofmx_id=data.runway_ofmx_id,
            airport_ofmx_id=data.airport_ofmx_id,
            designator=data.designator,
            true_bearing=None,
            mag_bearing=data.mag_bearing,
            latitude=data.latitude,
            longitude=data.longitude,
        )


def iter_airspaces(path: Path) -> Iterator[Airspace]:
    """Yield airspaces from an ARINC 424 dataset."""

    seen: set[str] = set()
    for line in _iter_lines(path):
        section = line[4:6]
        if section == "UC":
            airspace = _parse_controlled_airspace(line)
        elif section == "UR":
            airspace = _parse_restrictive_airspace(line)
        elif section == "UF":
            airspace = _parse_fir_uir(line)
        else:
            continue
        if airspace is None:
            continue
        if airspace.ofmx_id in seen:
            continue
        seen.add(airspace.ofmx_id)
        yield airspace


def iter_navaids(path: Path) -> Iterator[Navaid]:
    """Yield VHF and NDB navaids from an ARINC 424 dataset."""

    for line in _iter_lines(path):
        section = line[4:6]
        if section == "D ":
            yield _parse_vhf_navaid(line)
        elif section == "DB":
            yield _parse_ndb_navaid(line)


def iter_waypoints(path: Path) -> Iterator[Waypoint]:
    """Yield waypoints from an ARINC 424 dataset."""

    for line in _iter_lines(path):
        section = line[4:6]
        if section not in {"EA", "PC"}:
            continue
        if line[21] != "0":
            continue
        ident = _strip(line[13:18])
        if not ident:
            continue
        ofmx_id = _waypoint_id(section, ident, line[6:10])
        yield Waypoint(
            ofmx_id=ofmx_id,
            region=_strip(line[6:10]),
            code_id=ident,
            name=_strip(line[98:123]) or ident,
            point_type=_strip(line[26:29]),
            latitude=_parse_lat(line[32:41]),
            longitude=_parse_lon(line[41:51]),
        )


def iter_airspace_shapes(_: Path) -> Iterator[AirspaceShape]:
    """ARINC 424 datasets do not provide OFMX airspace shape extensions."""

    return iter(())


class _RunwayEndData:
    def __init__(
        self,
        *,
        runway_end_id: str,
        runway_ofmx_id: str,
        airport_ofmx_id: str,
        designator: str,
        pair_designator: str,
        length: Optional[int],
        width: Optional[int],
        mag_bearing: Optional[float],
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> None:
        self.runway_end_id = runway_end_id
        self.runway_ofmx_id = runway_ofmx_id
        self.airport_ofmx_id = airport_ofmx_id
        self.designator = designator
        self.pair_designator = pair_designator
        self.length = length
        self.width = width
        self.mag_bearing = mag_bearing
        self.latitude = latitude
        self.longitude = longitude


def _iter_runway_end_data(path: Path) -> Iterator[_RunwayEndData]:
    for line in _iter_lines(path):
        if not _is_section(line, "PG"):
            continue
        if line[21] != "0":
            continue
        airport = _strip(line[6:10])
        if not airport:
            continue
        designator = _normalize_runway_designator(_strip(line[13:18]))
        if designator is None:
            continue
        pair_key, pair_designator = _runway_pair(designator)
        runway_ofmx_id = _runway_id(airport, pair_key)
        runway_end_id = _runway_end_id(airport, designator)
        yield _RunwayEndData(
            runway_end_id=runway_end_id,
            runway_ofmx_id=runway_ofmx_id,
            airport_ofmx_id=_airport_id(airport),
            designator=designator,
            pair_designator=pair_designator,
            length=_to_int(line[22:27]),
            width=_to_int(line[77:80]),
            mag_bearing=_parse_bearing(line[27:31]),
            latitude=_parse_lat(line[32:41]),
            longitude=_parse_lon(line[41:51]),
        )


def _merge_runways(runway: Runway, data: _RunwayEndData) -> Runway:
    return Runway(
        ofmx_id=runway.ofmx_id,
        airport_ofmx_id=runway.airport_ofmx_id,
        designator=runway.designator,
        length=max(_as_int(runway.length), _as_int(data.length)) or None,
        width=max(_as_int(runway.width), _as_int(data.width)) or None,
        uom_dim_rwy=runway.uom_dim_rwy,
        surface=runway.surface,
        preparation=runway.preparation,
        pcn_note=runway.pcn_note,
        strip_length=runway.strip_length,
        strip_width=runway.strip_width,
        uom_dim_strip=runway.uom_dim_strip,
    )


def _parse_controlled_airspace(line: str) -> Optional[Airspace]:
    if line[24] != "0":
        return None
    icao = _strip(line[6:8])
    airspace_type = _strip(line[9])
    airspace_center = _strip(line[9:14])
    name = _strip(line[93:123])
    lower_ref, lower_value = _parse_limit(line[81:86])
    upper_ref, upper_value = _parse_limit(line[87:92])
    return Airspace(
        ofmx_id=f"ARINC:UC:{icao}:{airspace_center}:{airspace_type}",
        region=icao,
        code_id=airspace_center,
        code_type=airspace_type,
        name=name,
        name_alt=None,
        airspace_class=_strip(line[16]),
        upper_ref=upper_ref,
        upper_value=upper_value,
        upper_uom=_strip(line[92]),
        lower_ref=lower_ref,
        lower_value=lower_value,
        lower_uom=_strip(line[86]),
        remarks=None,
    )


def _parse_restrictive_airspace(line: str) -> Optional[Airspace]:
    if line[24] != "0":
        return None
    icao = _strip(line[6:8])
    restrictive_type = _strip(line[8])
    designation = _strip(line[9:19])
    name = _strip(line[93:123])
    lower_ref, lower_value = _parse_limit(line[82:86])
    upper_ref, upper_value = _parse_limit(line[87:92])
    return Airspace(
        ofmx_id=f"ARINC:UR:{icao}:{restrictive_type}:{designation}",
        region=icao,
        code_id=designation,
        code_type=restrictive_type,
        name=name,
        name_alt=None,
        airspace_class=None,
        upper_ref=upper_ref,
        upper_value=upper_value,
        upper_uom=_strip(line[92]),
        lower_ref=lower_ref,
        lower_value=lower_value,
        lower_uom=_strip(line[86]),
        remarks=None,
    )


def _parse_fir_uir(line: str) -> Optional[Airspace]:
    if line[19] != "0":
        return None
    ident = _strip(line[6:10])
    name = _strip(line[98:123])
    lower_ref, lower_value = _parse_limit(line[85:90])
    upper_ref, upper_value = _parse_limit(line[90:95])
    if lower_ref is None and lower_value is None:
        lower_ref, lower_value = _parse_limit(line[80:85])
    return Airspace(
        ofmx_id=f"ARINC:UF:{ident}",
        region=_strip(line[1:4]),
        code_id=ident,
        code_type=_strip(line[14]),
        name=name,
        name_alt=None,
        airspace_class=None,
        upper_ref=upper_ref,
        upper_value=upper_value,
        upper_uom=None,
        lower_ref=lower_ref,
        lower_value=lower_value,
        lower_uom=None,
        remarks=None,
    )


def _parse_vhf_navaid(line: str) -> Navaid:
    ident = _strip(line[13:17]) or ""
    icao = _strip(line[10:12])
    return Navaid(
        ofmx_id=f"ARINC:D:{icao}:{ident}",
        region=icao,
        code_id=ident,
        name=_strip(line[93:123]),
        navaid_type="VOR",
        code_type=None,
        frequency=_parse_frequency(line[22:27]),
        frequency_uom="MHz" if _strip(line[22:27]) else None,
        channel=None,
        ghost_frequency=None,
        elevation=_to_int(line[79:84]),
        elevation_uom="FT" if _strip(line[79:84]) else None,
        mag_var=_parse_mag_var(line[74:79]),
        datum=_strip(line[90:93]),
        associated_vor_ofmx_id=None,
        latitude=_parse_lat(line[32:41]),
        longitude=_parse_lon(line[41:51]),
    )


def _parse_ndb_navaid(line: str) -> Navaid:
    ident = _strip(line[13:17]) or ""
    icao = _strip(line[10:12])
    return Navaid(
        ofmx_id=f"ARINC:DB:{icao}:{ident}",
        region=icao,
        code_id=ident,
        name=_strip(line[93:123]),
        navaid_type="NDB",
        code_type=None,
        frequency=_parse_frequency(line[22:27]),
        frequency_uom="kHz" if _strip(line[22:27]) else None,
        channel=None,
        ghost_frequency=None,
        elevation=None,
        elevation_uom=None,
        mag_var=_parse_mag_var(line[74:79]),
        datum=_strip(line[90:93]),
        associated_vor_ofmx_id=None,
        latitude=_parse_lat(line[32:41]),
        longitude=_parse_lon(line[41:51]),
    )


def _iter_lines(path: Path) -> Iterator[str]:
    if path.suffix.lower() == ".zip":
        yield from _iter_zip_lines(path)
        return
    with path.open("r", encoding="ascii", errors="ignore") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue
            yield line


def _iter_zip_lines(path: Path) -> Iterator[str]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".pc")]
        if not members:
            return
        preferred = [name for name in members if "/isolated/" in name]
        target = preferred[0] if preferred else members[0]
        with archive.open(target) as handle:
            wrapper = io.TextIOWrapper(handle, encoding="ascii", errors="ignore")
            for line in wrapper:
                line = line.rstrip("\r\n")
                if not line:
                    continue
                yield line


def _is_section(line: str, section: str) -> bool:
    if line[4] == "P":
        return line[4] + line[12] == section
    return line[4:6] == section


def _airport_id(icao: str) -> str:
    return f"ARINC:PA:{icao}"


def _runway_id(airport: str, pair_key: str) -> str:
    return f"ARINC:PG:{airport}:{pair_key}"


def _runway_end_id(airport: str, designator: str) -> str:
    return f"ARINC:RD:{airport}:{designator}"


def _waypoint_id(section: str, ident: str, region: str | None) -> str:
    region_part = region or ""
    return f"ARINC:{section}:{region_part}:{ident}"


def _normalize_runway_designator(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if raw.upper().startswith("RW"):
        raw = raw[2:]
    raw = raw.strip()
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    side = "".join(ch for ch in raw if ch.isalpha()).upper()
    if not digits:
        return None
    number = int(digits)
    side = side[:1] if side else ""
    return f"{number:02d}{side}"


def _runway_pair(designator: str) -> tuple[str, str]:
    num = int(designator[:2])
    side = designator[2:] if len(designator) > 2 else ""
    reciprocal = (num + 18) % 36
    reciprocal = 36 if reciprocal == 0 else reciprocal
    reciprocal_side = {"L": "R", "R": "L", "C": "C", "": ""}.get(side, "")
    other = f"{reciprocal:02d}{reciprocal_side}"
    first, second = sorted([designator, other], key=_runway_sort_key)
    pair_key = f"{first}-{second}"
    pair_designator = f"{first}/{second}"
    return pair_key, pair_designator


def _runway_sort_key(designator: str) -> tuple[int, str]:
    number = int(designator[:2])
    side = designator[2:] if len(designator) > 2 else ""
    return number, side


def _strip(value: str) -> Optional[str]:
    stripped = value.strip()
    return stripped or None


def _to_int(value: str) -> Optional[int]:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _as_int(value: Optional[int]) -> int:
    return value or 0


def _parse_frequency(value: str) -> Optional[float]:
    value = value.strip()
    if not value:
        return None
    if not value.isdigit():
        return None
    return float(value) / 100.0


def _parse_bearing(value: str) -> Optional[float]:
    value = value.strip()
    if not value:
        return None
    if not value.isdigit():
        return None
    return float(int(value)) / 10.0


def _parse_mag_var(value: str) -> Optional[float]:
    value = value.strip()
    if not value:
        return None
    sign = 1.0
    if value[0] in {"W", "S", "-"}:
        sign = -1.0
    digits = value[1:] if value[0].isalpha() or value[0] in "+-" else value
    digits = digits.strip()
    if not digits.isdigit():
        return None
    magnitude = int(digits)
    if len(digits) >= 2:
        magnitude = magnitude / 10.0
    return sign * magnitude


def _parse_lat(value: str) -> Optional[float]:
    value = value.strip()
    if len(value) < 9:
        return None
    hemi = value[0].upper()
    digits = value[1:]
    try:
        deg = int(digits[0:2])
        minutes = int(digits[2:4])
        seconds = int(digits[4:6])
        hundredths = int(digits[6:8])
    except ValueError:
        return None
    result = deg + minutes / 60.0 + (seconds + hundredths / 100.0) / 3600.0
    if hemi == "S":
        result = -result
    return result


def _parse_lon(value: str) -> Optional[float]:
    value = value.strip()
    if len(value) < 10:
        return None
    hemi = value[0].upper()
    digits = value[1:]
    try:
        deg = int(digits[0:3])
        minutes = int(digits[3:5])
        seconds = int(digits[5:7])
        hundredths = int(digits[7:9])
    except ValueError:
        return None
    result = deg + minutes / 60.0 + (seconds + hundredths / 100.0) / 3600.0
    if hemi == "W":
        result = -result
    return result


def _parse_limit(raw: str) -> tuple[Optional[str], Optional[int]]:
    value = raw.strip()
    if not value:
        return None, None
    if value in {"GND", "SFC", "UNL", "UNLTD"}:
        return value, None
    if value.startswith("FL") and value[2:].isdigit():
        return "FL", int(value[2:])
    if value.isdigit():
        return None, int(value)
    if value[:2].isalpha() and value[2:].isdigit():
        return value[:2], int(value[2:])
    return value, None
