"""OpenAIR airspace parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional
import io
import re
import unicodedata
import zipfile


@dataclass(frozen=True)
class OpenAirspace:
    name: str
    airspace_class: Optional[str]
    lower: Optional[str]
    upper: Optional[str]
    positions: list[tuple[float, float]]


def iter_airspaces(path: Path) -> Iterator[OpenAirspace]:
    """Yield airspaces from an OpenAIR dataset."""

    current_name: Optional[str] = None
    current_class: Optional[str] = None
    current_lower: Optional[str] = None
    current_upper: Optional[str] = None
    positions: list[tuple[float, float]] = []

    def flush() -> Iterator[OpenAirspace]:
        nonlocal current_name, current_class, current_lower, current_upper, positions
        if current_name and positions:
            yield OpenAirspace(
                name=current_name,
                airspace_class=current_class,
                lower=current_lower,
                upper=current_upper,
                positions=positions,
            )
        current_name = None
        current_class = None
        current_lower = None
        current_upper = None
        positions = []

    for raw in _iter_lines(path):
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("AC "):
            yield from flush()
            current_class = line[3:].strip() or None
            continue
        if line.startswith("AN "):
            current_name = line[3:].strip() or None
            continue
        if line.startswith("AL "):
            current_lower = line[3:].strip() or None
            continue
        if line.startswith("AH "):
            current_upper = line[3:].strip() or None
            continue
        if line.startswith("DP "):
            coord = _parse_dp(line[3:])
            if coord:
                positions.append(coord)
            continue
    yield from flush()


def build_shape_index(path: Path) -> dict[tuple[str, Optional[str]], list[tuple[float, float]]]:
    shapes: dict[tuple[str, Optional[str]], list[tuple[float, float]]] = {}
    for airspace in iter_airspaces(path):
        key = (_normalize_name(airspace.name), _normalize_class(airspace.airspace_class))
        if key not in shapes:
            shapes[key] = airspace.positions
        fallback = (_normalize_name(airspace.name), None)
        if fallback not in shapes:
            shapes[fallback] = airspace.positions
    return shapes


def _iter_lines(path: Path) -> Iterator[str]:
    if path.suffix.lower() == ".zip":
        yield from _iter_zip_lines(path)
        return
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            yield line.rstrip("\r\n")


def _iter_zip_lines(path: Path) -> Iterator[str]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".txt")]
        if not members:
            return
        preferred = [name for name in members if "/isolated/" in name and "seeyou" in name]
        target = preferred[0] if preferred else members[0]
        with archive.open(target) as handle:
            wrapper = io.TextIOWrapper(handle, encoding="utf-8", errors="ignore")
            for line in wrapper:
                yield line.rstrip("\r\n")


def _parse_dp(value: str) -> Optional[tuple[float, float]]:
    tokens = value.replace(",", " ").split()
    if not tokens:
        return None
    lat, lon = _split_coord(tokens)
    if lat is None or lon is None:
        return None
    return lon, lat


def _split_coord(tokens: list[str]) -> tuple[Optional[float], Optional[float]]:
    lat_tokens: list[str] = []
    lon_tokens: list[str] = []
    hemi_lat = None
    hemi_lon = None
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token[-1] in {"N", "S"}:
            hemi_lat = token[-1]
            lat_tokens.append(token[:-1])
            idx += 1
            break
        if token in {"N", "S"}:
            hemi_lat = token
            idx += 1
            break
        lat_tokens.append(token)
        idx += 1
    while idx < len(tokens):
        token = tokens[idx]
        if token[-1] in {"E", "W"}:
            hemi_lon = token[-1]
            lon_tokens.append(token[:-1])
            idx += 1
            break
        if token in {"E", "W"}:
            hemi_lon = token
            idx += 1
            break
        lon_tokens.append(token)
        idx += 1
    lat = _parse_dms("".join(lat_tokens), hemi_lat)
    lon = _parse_dms("".join(lon_tokens), hemi_lon)
    return lat, lon


def _parse_dms(value: str, hemisphere: Optional[str]) -> Optional[float]:
    if not value:
        return None
    value = value.strip()
    if hemisphere is None and value[0] in "NSEW":
        hemisphere = value[0]
        value = value[1:]
    parts = value.split(":")
    try:
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0.0
        seconds = float(parts[2]) if len(parts) > 2 else 0.0
    except (ValueError, IndexError):
        return None
    result = degrees + minutes / 60.0 + seconds / 3600.0
    if hemisphere in {"S", "W"}:
        result = -result
    return result


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = normalized.strip().upper().split()
    while tokens and re.fullmatch(r"\d+\.\d+", tokens[-1]):
        tokens.pop()
    return " ".join(tokens)


def _normalize_class(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip().upper() or None
