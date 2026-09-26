# Nurtura developer commands. Works on Mac/Linux, WSL and Git Bash on Windows.
# Native Windows without make: see "Common Commands" in README.md.

BACKEND  := backend
APP      := mobile/nurtura_app
VENV     := $(BACKEND)/venv

# venv layout differs: venv/Scripts on Windows, venv/bin elsewhere.
ifeq ($(OS),Windows_NT)
  VENV_BIN   := $(VENV)/Scripts
  SYS_PYTHON ?= python
else
  VENV_BIN   := $(VENV)/bin
  SYS_PYTHON ?= python3
endif
PY := $(abspath $(VENV_BIN))/python

.PHONY: setup run-backend run-app seed-data test

## setup: create venv, install backend + mobile deps, cache SBERT model, install git hooks
setup:
	test -d $(VENV) || $(SYS_PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r $(BACKEND)/requirements.txt
	test -f $(BACKEND)/.env || cp $(BACKEND)/.env.example $(BACKEND)/.env
	cd $(BACKEND) && $(PY) setup_sbert.py
	cd $(APP) && flutter pub get
	$(PY) -m pre_commit install

## run-backend: start the Django dev server on http://127.0.0.1:8000
run-backend:
	cd $(BACKEND) && $(PY) manage.py runserver

## run-app: run the Flutter app (pass DEVICE=chrome or an emulator id)
run-app:
	cd $(APP) && flutter run $(if $(DEVICE),-d $(DEVICE),)

## seed-data: validate raw activities into data/processed/
seed-data:
	cd data/scripts && $(PY) clean_activities.py ../raw/activities_batch1.csv ../processed/activities_clean.csv

## test: backend checks + tests, Flutter analyze + tests
test:
	cd $(BACKEND) && $(PY) manage.py check
	cd $(BACKEND) && $(PY) manage.py makemigrations --check --dry-run
	cd $(BACKEND) && $(PY) manage.py test
	cd $(APP) && flutter analyze
	cd $(APP) && flutter test
