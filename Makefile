.PHONY: run
run:
	python -m app.main

.PHONY: test
test:
	pytest -v

.PHONY: test-unit
test-unit:
	pytest -v -m "not integration"

.PHONY: test-integration
test-integration:
	pytest -v -m integration

.PHONY: migration
migration:
	bash scripts/migrate.sh

.PHONY: worker
worker:
	python -m app.workers.moderation_worker

.PHONY: docker-up
docker-up:
	docker-compose up -d

.PHONY: docker-down
docker-down:
	docker-compose down

.PHONY: docker-logs
docker-logs:
	docker-compose logs -f