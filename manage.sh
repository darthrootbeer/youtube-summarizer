#!/usr/bin/env bash
# Entry point — delegates to scripts/manage.sh
exec "$(dirname "$0")/scripts/manage.sh" "$@"
