FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY sql /app/sql
COPY scripts /app/scripts

RUN pip install --no-cache-dir .

ENV OFMX_URL="https://snapshots.openflightmaps.org/live/2513/ofmx/lkaa/latest/ofmx_lk.zip" \
    ARINC_URL="" \
    OPENAIR_URL="" \
    OFMX_DEST="/data" \
    PG_SCHEMA="ofmx" \
    APPLY_MIGRATIONS="true" \
    DRY_RUN="false" \
    VERBOSE="true"

ENTRYPOINT ["/app/scripts/fetch_import.sh"]
