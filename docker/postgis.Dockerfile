FROM postgres:18-alpine

RUN apk add --no-cache postgis \
    && rm -rf /usr/local/share/postgresql/extension \
    && ln -s /usr/share/postgresql18/extension /usr/local/share/postgresql/extension \
    && ln -sf /usr/lib/postgresql18/postgis-3.so /usr/local/lib/postgresql/postgis-3.so \
    && ln -sf /usr/lib/postgresql18/rtpostgis-3.so /usr/local/lib/postgresql/rtpostgis-3.so \
    && ln -sf /usr/lib/postgresql18/postgis_sfcgal-3.so /usr/local/lib/postgresql/postgis_sfcgal-3.so
