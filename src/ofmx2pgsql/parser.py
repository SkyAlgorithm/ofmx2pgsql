"""OFMX parsing utilities for OFMX-Snapshot 0.1 datasets."""

from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Iterator, Optional


@dataclass(frozen=True)
class ParsedDataset:
    """Metadata for a parsed OFMX dataset."""

    source_path: Path


@dataclass(frozen=True)
class Airport:
    ofmx_id: str
    region: Optional[str]
    code_id: Optional[str]
    code_icao: Optional[str]
    code_gps: Optional[str]
    code_type: Optional[str]
    name: Optional[str]
    city: Optional[str]
    elevation: Optional[int]
    elevation_uom: Optional[str]
    mag_var: Optional[float]
    mag_var_year: Optional[int]
    transition_alt: Optional[int]
    transition_alt_uom: Optional[str]
    remarks: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


@dataclass(frozen=True)
class Runway:
    ofmx_id: str
    airport_ofmx_id: Optional[str]
    designator: Optional[str]
    length: Optional[int]
    width: Optional[int]
    uom_dim_rwy: Optional[str]
    surface: Optional[str]
    preparation: Optional[str]
    pcn_note: Optional[str]
    strip_length: Optional[int]
    strip_width: Optional[int]
    uom_dim_strip: Optional[str]


@dataclass(frozen=True)
class RunwayEnd:
    ofmx_id: str
    runway_ofmx_id: Optional[str]
    airport_ofmx_id: Optional[str]
    designator: Optional[str]
    true_bearing: Optional[float]
    mag_bearing: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]


@dataclass(frozen=True)
class Airspace:
    ofmx_id: str
    region: Optional[str]
    code_id: Optional[str]
    code_type: Optional[str]
    name: Optional[str]
    name_alt: Optional[str]
    airspace_class: Optional[str]
    upper_ref: Optional[str]
    upper_value: Optional[int]
    upper_uom: Optional[str]
    lower_ref: Optional[str]
    lower_value: Optional[int]
    lower_uom: Optional[str]
    remarks: Optional[str]


@dataclass(frozen=True)
class Navaid:
    ofmx_id: str
    region: Optional[str]
    code_id: Optional[str]
    name: Optional[str]
    navaid_type: str
    code_type: Optional[str]
    frequency: Optional[float]
    frequency_uom: Optional[str]
    channel: Optional[str]
    ghost_frequency: Optional[float]
    elevation: Optional[int]
    elevation_uom: Optional[str]
    mag_var: Optional[float]
    datum: Optional[str]
    associated_vor_ofmx_id: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


@dataclass(frozen=True)
class Waypoint:
    ofmx_id: str
    region: Optional[str]
    code_id: Optional[str]
    name: Optional[str]
    point_type: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]


@dataclass(frozen=True)
class AirspaceShape:
    ofmx_id: str
    positions: list[tuple[float, float]]


Record = Airport | Runway | RunwayEnd | Airspace | Navaid | Waypoint


def iter_ofmx_files(root: Path) -> Iterable[Path]:
    """Yield OFMX XML files from a directory tree."""

    if root.is_file() and root.suffix == ".ofmx":
        yield root
        return

    if not root.is_dir():
        return

    for path in sorted(root.rglob("*.ofmx")):
        yield path


def parse_dataset(path: Path) -> ParsedDataset:
    """Parse an OFMX dataset, returning a metadata-only placeholder."""

    return ParsedDataset(source_path=path)


def iter_airports(path: Path) -> Iterator[Airport]:
    """Yield airports (Ahp)."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "Ahp":
            continue
        ahp_uid = elem.find("AhpUid")
        if ahp_uid is None:
            elem.clear()
            continue
        yield Airport(
            ofmx_id=ahp_uid.get("mid", ""),
            region=ahp_uid.get("region"),
            code_id=_text(ahp_uid, "codeId"),
            code_icao=_text(elem, "codeIcao"),
            code_gps=_text(elem, "codeGps"),
            code_type=_text(elem, "codeType"),
            name=_text(elem, "txtName"),
            city=_text(elem, "txtNameCitySer"),
            elevation=_to_int(_text(elem, "valElev")),
            elevation_uom=_text(elem, "uomDistVer"),
            mag_var=_to_float(_text(elem, "valMagVar")),
            mag_var_year=_to_int(_text(elem, "dateMagVar")),
            transition_alt=_to_int(_text(elem, "valTransitionAlt")),
            transition_alt_uom=_text(elem, "uomTransitionAlt"),
            remarks=_text(elem, "txtRmk"),
            latitude=_parse_coordinate(_text(elem, "geoLat")),
            longitude=_parse_coordinate(_text(elem, "geoLong")),
        )
        elem.clear()


def iter_runways(path: Path) -> Iterator[Runway]:
    """Yield runways (Rwy)."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "Rwy":
            continue
        rwy_uid = elem.find("RwyUid")
        if rwy_uid is None:
            elem.clear()
            continue
        ahp_uid = rwy_uid.find("AhpUid")
        yield Runway(
            ofmx_id=rwy_uid.get("mid", ""),
            airport_ofmx_id=ahp_uid.get("mid") if ahp_uid is not None else None,
            designator=_text(rwy_uid, "txtDesig"),
            length=_to_int(_text(elem, "valLen")),
            width=_to_int(_text(elem, "valWid")),
            uom_dim_rwy=_text(elem, "uomDimRwy"),
            surface=_text(elem, "codeComposition"),
            preparation=_text(elem, "codePreparation"),
            pcn_note=_text(elem, "txtPcnNote"),
            strip_length=_to_int(_text(elem, "valLenStrip")),
            strip_width=_to_int(_text(elem, "valWidStrip")),
            uom_dim_strip=_text(elem, "uomDimStrip"),
        )
        elem.clear()


def iter_runway_ends(path: Path) -> Iterator[RunwayEnd]:
    """Yield runway ends (Rdn)."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "Rdn":
            continue
        rdn_uid = elem.find("RdnUid")
        if rdn_uid is None:
            elem.clear()
            continue
        rwy_uid = rdn_uid.find("RwyUid")
        ahp_uid = rwy_uid.find("AhpUid") if rwy_uid is not None else None
        yield RunwayEnd(
            ofmx_id=rdn_uid.get("mid", ""),
            runway_ofmx_id=rwy_uid.get("mid") if rwy_uid is not None else None,
            airport_ofmx_id=ahp_uid.get("mid") if ahp_uid is not None else None,
            designator=_text(rdn_uid, "txtDesig"),
            true_bearing=_to_float(_text(elem, "valTrueBrg")),
            mag_bearing=_to_float(_text(elem, "valMagBrg")),
            latitude=_parse_coordinate(_text(elem, "geoLat")),
            longitude=_parse_coordinate(_text(elem, "geoLong")),
        )
        elem.clear()


def iter_airspaces(path: Path) -> Iterator[Airspace]:
    """Yield airspaces (Ase)."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "Ase":
            continue
        ase_uid = elem.find("AseUid")
        if ase_uid is None:
            elem.clear()
            continue
        yield Airspace(
            ofmx_id=ase_uid.get("mid", ""),
            region=ase_uid.get("region"),
            code_id=_text(ase_uid, "codeId"),
            code_type=_text(ase_uid, "codeType"),
            name=_text(elem, "txtName"),
            name_alt=_text(elem, "txtNameAlt"),
            airspace_class=_text(elem, "codeClass"),
            upper_ref=_text(elem, "codeDistVerUpper"),
            upper_value=_to_int(_text(elem, "valDistVerUpper")),
            upper_uom=_text(elem, "uomDistVerUpper"),
            lower_ref=_text(elem, "codeDistVerLower"),
            lower_value=_to_int(_text(elem, "valDistVerLower")),
            lower_uom=_text(elem, "uomDistVerLower"),
            remarks=_text(elem, "txtRmk"),
        )
        elem.clear()


def iter_waypoints(path: Path) -> Iterator[Waypoint]:
    """Yield designated points (Dpn)."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "Dpn":
            continue
        dpn_uid = elem.find("DpnUid")
        if dpn_uid is None:
            elem.clear()
            continue
        yield Waypoint(
            ofmx_id=dpn_uid.get("mid", ""),
            region=dpn_uid.get("region"),
            code_id=_text(dpn_uid, "codeId"),
            name=_text(elem, "txtName"),
            point_type=_text(elem, "codeType"),
            latitude=_parse_coordinate(_text(dpn_uid, "geoLat")),
            longitude=_parse_coordinate(_text(dpn_uid, "geoLong")),
        )
        elem.clear()


def iter_navaids(path: Path) -> Iterator[Navaid]:
    """Yield NDB, VOR, and DME records."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag not in {"Ndb", "Vor", "Dme"}:
            continue
        uid_tag = f"{elem.tag}Uid"
        navaid_uid = elem.find(uid_tag)
        if navaid_uid is None:
            elem.clear()
            continue
        vor_uid = elem.find("VorUid") if elem.tag == "Dme" else None
        yield Navaid(
            ofmx_id=navaid_uid.get("mid", ""),
            region=navaid_uid.get("region"),
            code_id=_text(navaid_uid, "codeId"),
            name=_text(elem, "txtName"),
            navaid_type=elem.tag.upper(),
            code_type=_text(elem, "codeType"),
            frequency=_to_float(_text(elem, "valFreq")),
            frequency_uom=_text(elem, "uomFreq"),
            channel=_text(elem, "codeChannel"),
            ghost_frequency=_to_float(_text(elem, "valGhostFreq")),
            elevation=_to_int(_text(elem, "valElev")),
            elevation_uom=_text(elem, "uomDistVer"),
            mag_var=_to_float(_text(elem, "valMagVar")),
            datum=_text(elem, "codeDatum"),
            associated_vor_ofmx_id=vor_uid.get("mid") if vor_uid is not None else None,
            latitude=_parse_coordinate(_text(navaid_uid, "geoLat")),
            longitude=_parse_coordinate(_text(navaid_uid, "geoLong")),
        )
        elem.clear()


def iter_airspace_shapes(path: Path) -> Iterator[AirspaceShape]:
    """Yield airspace shapes from the OFM shape extension file."""

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "Ase":
            continue
        ase_uid = elem.find("AseUid")
        if ase_uid is None:
            elem.clear()
            continue
        gml = _text(elem, "gmlPosList")
        positions = _parse_gml_pos_list(gml)
        if positions:
            yield AirspaceShape(ofmx_id=ase_uid.get("mid", ""), positions=positions)
        elem.clear()


def _text(elem: ET.Element, tag: str) -> Optional[str]:
    child = elem.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_coordinate(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    raw = value.strip()
    hemisphere = raw[-1].upper() if raw[-1].isalpha() else ""
    number = raw[:-1] if hemisphere else raw
    try:
        parsed = float(number)
    except ValueError:
        return None
    if hemisphere in {"S", "W"}:
        return -parsed
    return parsed


def _parse_gml_pos_list(value: Optional[str]) -> list[tuple[float, float]]:
    if not value:
        return []
    points: list[tuple[float, float]] = []
    for token in value.split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        points.append((lon, lat))
    return points
