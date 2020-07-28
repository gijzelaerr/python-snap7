# developer file, not intented for installing python-snap7

all: test

venv/:
	python3 -m venv venv
	venv/bin/pip install --upgrade pip wheel

venv/installed: venv/
	venv/bin/pip install -e ".[test,doc]"
	touch venv/installed

setup: venv/installed

test: setup
	sudo venv/bin/pytest test/test_partner.py
	venv/bin/pytest test/test_server.py
	venv/bin/pytest test/test_client.py
	venv/bin/pytest test/test_util.py

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
