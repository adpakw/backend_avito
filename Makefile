.PHONY: run
run:
	python -m app.main

.PHONY: test
test:
	pytest -v

.PHONY: migration
migration:
	bash scripts/migrate.sh

.PHONY: worker
worker:
	python -m app.workers.moderation_worker