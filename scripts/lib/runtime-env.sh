#!/usr/bin/env bash
# Load runtime dotenv files — same sources Alpha OS uses in Python.

_load_dotenv_file() {
  local env_file="$1"
  [[ -f "${env_file}" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
}

load_hermes_env() {
  _load_dotenv_file "${HOME}/.hermes/.env"
}

load_openclaw_env() {
  local state_dir="${OPENCLAW_STATE_DIR:-${HOME}/.openclaw}"
  _load_dotenv_file "${state_dir}/.env"
}

load_runtime_env() {
  load_hermes_env
  load_openclaw_env
}