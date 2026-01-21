.PHONY: run
run:
	poetry run python -m app.main

.PHONY: test
test:
	poetry run pytest -v
