#!/usr/bin/env bash
set -euo pipefail

OFMX_URL="${OFMX_URL:-${1:-https://snapshots.openflightmaps.org/live/2513/ofmx/lkaa/latest/ofmx_lk.zip}}"
OUT_DIR="${OUT_DIR:-data}"
ZIP_PATH="${ZIP_PATH:-${OUT_DIR}/ofmx_lk.zip}"
EXTRACT_DIR="${EXTRACT_DIR:-${OUT_DIR}/ofmx_lk}"

if ! command -v unzip >/dev/null 2>&1; then
  echo "Error: unzip is required." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

if command -v curl >/dev/null 2>&1; then
  curl -fL "${OFMX_URL}" -o "${ZIP_PATH}"
elif command -v wget >/dev/null 2>&1; then
  wget -O "${ZIP_PATH}" "${OFMX_URL}"
else
  echo "Error: curl or wget is required to download OFMX data." >&2
  exit 1
fi

rm -rf "${EXTRACT_DIR}"
unzip -q "${ZIP_PATH}" -d "${EXTRACT_DIR}"

echo "Downloaded to ${ZIP_PATH}"
echo "Extracted to ${EXTRACT_DIR}"
