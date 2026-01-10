#!/usr/bin/env sh
set -eu

if [ -z "${PG_DSN:-}" ]; then
  echo "PG_DSN is required (example: postgresql://user:pass@host:5432/db)" >&2
  exit 1
fi

OFMX_URL=${OFMX_URL:-"https://snapshots.openflightmaps.org/live/2513/ofmx/lkaa/latest/ofmx_lk.zip"}
OFMX_DEST=${OFMX_DEST:-"/data"}
PG_SCHEMA=${PG_SCHEMA:-"ofmx"}
APPLY_MIGRATIONS=${APPLY_MIGRATIONS:-"true"}
DRY_RUN=${DRY_RUN:-"false"}
VERBOSE=${VERBOSE:-"true"}

mkdir -p "$OFMX_DEST"
archive="$OFMX_DEST/ofmx_snapshot.zip"

echo "Downloading $OFMX_URL"
curl -fsSL "$OFMX_URL" -o "$archive"

rm -rf "$OFMX_DEST/ofmx"
mkdir -p "$OFMX_DEST/ofmx"
unzip -q "$archive" -d "$OFMX_DEST/ofmx"

ofmx_file=$(find "$OFMX_DEST/ofmx" -name "*.ofmx" -print -quit)
shape_file=$(find "$OFMX_DEST/ofmx" -name "*_ofmShapeExtension.xml" -print -quit || true)

if [ -z "$ofmx_file" ]; then
  echo "No .ofmx file found in the downloaded archive." >&2
  exit 1
fi

cmd="python -m ofmx2pgsql import --dsn $PG_DSN --schema $PG_SCHEMA --ofmx $ofmx_file"
if [ -n "$shape_file" ]; then
  cmd="$cmd --shapes $shape_file"
fi
if [ "$APPLY_MIGRATIONS" = "true" ]; then
  cmd="$cmd --apply-migrations"
fi
if [ "$DRY_RUN" = "true" ]; then
  cmd="$cmd --dry-run"
fi
if [ "$VERBOSE" = "true" ]; then
  cmd="$cmd --verbose"
fi

echo "Running: $cmd"
exec sh -c "$cmd"
