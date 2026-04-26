#!/usr/bin/env bash
# Seed demo companies and sample anchored bundles.
set -euo pipefail
uv run python -m veritext.cli.seed
