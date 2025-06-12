.PHONY: test lint format

test:
	pytest --cov=payme --cov-report=term-missing tests -v

lint:
	flake8 payme tests

format:
	black payme tests

run-example:
	python3 example.py