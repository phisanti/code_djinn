#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NEBULA_TOKEN:-}" ]]; then
  echo "NEBULA_TOKEN is missing"
  exit 2
fi

python - <<'PY'
from djinn_sample.app import build_status
print(build_status()["status"])
PY
