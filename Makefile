.PHONY: run
run:
	python -m app.main

.PHONY: test
test:
	pytest -v
