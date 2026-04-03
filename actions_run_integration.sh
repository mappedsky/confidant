#!/bin/bash

cd /srv/confidant
apt-get update && apt-get install -y python3-dev openssl libssl-dev gcc pkg-config libffi-dev
pip install -r piptools_requirements.txt && pip install -r requirements.txt
make test_integration
