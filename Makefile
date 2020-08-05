# developer file, not intented for installing python-snap7

.PHONY: test

allll: test

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
	venv/bin/pytest test/test_server.py test/test_client.py test/test_util.py test/test_client_async.py
	sudo venv/bin/pytest test/test_partner.py  # run this as last to prevent pytest cache dir creates as root

docker-doc:
		docker build . -f .travis/doc.docker -t doc

docker-mypy:
	docker build . -f .travis/mypy.docker -t mypy

docker-pycodestyle:
	docker build . -f .travis/pycodestyle.docker -t pycodestyle

docker-ubuntu1804:
	docker build . -f .travis/ubuntu1804.docker -t ubuntu1804

docker-ubuntu2004:
	docker build . -f .travis/ubuntu2004.docker -t ubuntu2004

dockers: docker-doc docker-mypy docker-pycodestyle docker-ubuntu1804 docker-ubuntu2004
