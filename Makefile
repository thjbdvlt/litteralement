_pip=$(CURDIR)/venv/bin/pip3

all:
	make .gitignore

venv: .gitignore
	python -m venv venv

installer_venv: venv
	$(_pip) install -r ./requirements.txt
	$(_pip) install .
	bash ./scripts/installer-tokentype.sh

.gitignore:
	echo 'venv' > .gitignore
