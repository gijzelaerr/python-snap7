# developer file, not intended for installing python-snap7

.PHONY: test setup doc mypy test pycodestyle

all: test

venv/:
	python3 -m venv venv
	venv/bin/pip install --upgrade pip wheel

venv/installed: venv/
	venv/bin/pip install -e .
	touch venv/installed

setup: venv/installed

venv/bin/pytest: venv/
	venv/bin/pip install -e ".[test]"

venv/bin/pytest-asyncio: venv/
	venv/bin/pip install -e ".[test]"

venv/bin/sphinx-build:  venv/
	venv/bin/pip install -e ".[doc]"

doc: venv/bin/sphinx-build
	cd doc && make html

pycodestyle: venv/bin/pytest
	venv/bin/pycodestyle snap7 test

mypy: venv/bin/pytest
	venv/bin/mypy snap7 test

test: venv/bin/pytest
	venv/bin/pytest test/test_server.py test/test_client.py test/test_util.py test/test_mainloop.py
	sudo venv/bin/pytest test/test_partner.py  # run this as last to prevent pytest cache dir creates as root

clean:
	rm -rf venv python_snap7.egg-info .pytest_cache .tox dist .eggs