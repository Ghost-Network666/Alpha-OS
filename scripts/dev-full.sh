#!/usr/bin/env bash
# Alias for scripts/start.sh (kept for backwards compatibility)
exec "$(cd "$(dirname "$0")" && pwd)/start.sh" "$@"