#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q src mcp
python -m unittest discover -s tests -v