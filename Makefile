.PHONY: docker-build docker-import

docker-build:
	docker build -t ofmx2pgsql .

docker-import:
	docker run --rm \
		-e PG_DSN="${PG_DSN}" \
		-e OFMX_URL="${OFMX_URL}" \
		-e PG_SCHEMA="${PG_SCHEMA}" \
		-e APPLY_MIGRATIONS="${APPLY_MIGRATIONS}" \
		ofmx2pgsql
