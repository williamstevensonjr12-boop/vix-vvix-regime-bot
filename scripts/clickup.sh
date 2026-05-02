#!/usr/bin/env bash
# clickup.sh — DEPRECATED. ClickUp was dropped on 2026-05-01; ntfy is the
# notification path. This shim forwards all calls to scripts/notify.sh so
# any existing callers (routines, scripts that reference the old name) keep
# working. New callers should use notify.sh directly.
exec "$(dirname "$0")/notify.sh" "$@"
