#!/bin/bash
# Test runner that properly sets PYTHONPATH for the project

export PYTHONPATH="/workspaces/span:${PYTHONPATH}"
cd /workspaces/span

# Run poetry with the correct PYTHONPATH
poetry run pytest "$@"
