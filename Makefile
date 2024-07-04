# developer file, not intended for installing python-snap7

.PHONY: test setup doc mypy test pycodestyle

all: test

venv/:
	python3 -m venv venv
	venv/bin/pip install --upgrade pip wheel

venv/installed: venv/
	venv/bin/pip install -e .
	touch venv/installed

venv/bin/pytest: venv/
	venv/bin/pip install -e ".[test]"

venv/bin/sphinx-build:  venv/
	venv/bin/pip install -e ".[doc]"

venv/bin/tox: venv/
	venv/bin/pip install tox

requirements-dev.txt: venv/bin/tox pyproject.toml
	venv/bin/tox -e requirements-dev

.PHONY: setup
setup: venv/installed

.PHONY: doc
doc: venv/bin/sphinx-build
	cd doc && make html

.PHONY: check
check: venv/bin/pytest
	venv/bin/ruff check snap7 tests example
	 venv/bin/ruff format --diff snap7 tests example

.PHONY: ruff
ruff: venv/bin/tox
	venv/bin/tox -e ruff

.PHONY: format
format: ruff

.PHONY: mypy
mypy: venv/bin/tox
	venv/bin/tox -e mypy

.PHONY: test
test: venv/bin/pytest
	venv/bin/pytest

.PHONY: clean
clean:
	rm -rf venv python_snap7.egg-info .pytest_cache .tox dist .eggs

.PHONY: tox
tox: venv/bin/tox
	venv/bin/tox

.PHONY: requirements
requirements: requirements-dev.txt
