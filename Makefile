dbname=litteralement
_py=$(CURDIR)/venv/bin/python3
_pip=$(CURDIR)/venv/bin/pip3

all:
	make .gitignore
	make construire

construire:
	psql -c 'create database $(dbname)'
	psql $(dbname) < ./schema/tables.sql

venv: .gitignore
	python -m venv venv

installer_venv: venv
	$(_pip) install -r ./requirements.txt
	$(_pip) install .
	bash ./scripts/installer-tokentype.sh

.gitignore:
	echo 'venv' > .gitignore
