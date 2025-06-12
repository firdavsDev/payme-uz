.PHONY: test lint format

test:
	pytest --cov=payme --cov-report=term-missing tests -v

lint:
	flake8 --ignore=E501 src/**/*.py

format:
	black src/**/*.py

run-example:
	python3 example.py
	