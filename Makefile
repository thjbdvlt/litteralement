dbname=litteralement
_py=$(CURDIR)/venv/bin/python3
_pip=$(CURDIR)/venv/bin/pip3

all:
	make .gitignore
	make installer

construire:
	psql -c 'drop database $(dbname)'
	psql -c 'create database $(dbname)'
	psql $(dbname) < ./schema/tables.sql

venv:
	python -3 venv venv

installer: venv
	$(_pip) install -r ./requirements.txt
	$(_pip) install .
	bash ./scripts/installer-tokentype.sh

.gitignore:
	echo 'venv' > .gitignore
