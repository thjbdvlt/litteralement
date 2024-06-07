_py=$(CURDIR)/venv/bin/python3
_pip=$(CURDIR)/venv/bin/pip3

all:
	make .gitignore
	make installer

venv:
	python -3 venv venv

installer: venv
	$(_pip) install -r ./requirements.txt

.gitignore:
	echo 'venv' > .gitignore