"""OFMX parsing utilities (placeholder)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ParsedDataset:
    """Metadata for a parsed OFMX dataset."""

    source_path: Path


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
