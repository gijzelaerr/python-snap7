# developer file, not intended for installing python-snap7

.PHONY: test setup doc mypy test pycodestyle

all: test

.venv/:
	uv venv

.venv/installed: .venv/
	uv pip install -e .
	touch .venv/installed

.venv/bin/pytest: .venv/
	uv pip install -e ".[test]"

.venv/bin/sphinx-build:  .venv/
	uv pip install -e ".[doc,cli]"

.venv/bin/tox: .venv/
	uv pip install tox tox-uv

.PHONY: setup
setup: .venv/installed

.PHONY: doc
doc: .venv/bin/sphinx-build
	uv run sphinx-build -N -bhtml doc/ doc/_build

.PHONY: check
check: .venv/bin/pytest
	 uv run ruff check snap7 tests example
	 uv run ruff format --diff snap7 tests example

.PHONY: ruff
ruff: .venv/bin/tox
	uv run tox -e ruff

.PHONY: format
format: ruff

.PHONY: mypy
mypy: .venv/bin/tox
	uv run tox -e mypy

.PHONY: test
test: .venv/bin/pytest
	uv run pytest

.PHONY: clean
clean:
	rm -rf .venv python_snap7.egg-info .pytest_cache .tox dist .eggs

.PHONY: tox
tox: .venv/bin/tox
	uv run tox
