#!/bin/bash

pip install pip-tools

pip-compile requirements.in
pip-compile requirements-dev.in
pip-sync requirements-dev.txt && pip install -e .