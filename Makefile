.PHONY: test lint format run-example

test:
	pytest --cov=payme --cov-report=term-missing tests -v

lint:
	flake8 --ignore=E501 src/payme/*.py tests/*.py examples/*.py
	ruff check src tests examples

format:
	black src tests examples
	ruff check --fix src tests examples

run-example:
	PYTHONPATH=src python examples/example.py
