.PHONY: check nice test

check: nice test

nice:
	poetry run black src/
	poetry run mypy src/

test:
	poetry run pytest src/
