#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "${script_dir}/.." && pwd)"
game_root="${LGPE_GAME_ROOT:-$(dirname -- "${project_root}")}"
if ! command -v uv >/dev/null 2>&1; then
  printf 'uv was not found on PATH. Install the Linux uv runtime or set PATH, then retry.\n' >&2
  exit 127
fi
if [[ -z "${UV_PROJECT_ENVIRONMENT:-}" ]]; then
  UV_PROJECT_ENVIRONMENT="${LGPE_UV_ENVIRONMENT:-/tmp/lgpe-research-wsl-venv}"
  export UV_PROJECT_ENVIRONMENT
fi
cd -- "${project_root}"
uv sync
run_status=0
uv run lgpe run --root "${game_root}" "$@" || run_status=$?
test_status=0
uv run python -m unittest discover -s tests -v || test_status=$?
if (( run_status != 0 )); then
  printf 'LGPE run exited %s; unit tests exited %s. Inspect manifests/ and logs/.\n' "${run_status}" "${test_status}" >&2
  exit "${run_status}"
fi
exit "${test_status}"
