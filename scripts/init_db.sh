#!/usr/bin/env bash
set -e
cd "$(dirname "$(dirname "$0")")"
python3 main.py --init-db
