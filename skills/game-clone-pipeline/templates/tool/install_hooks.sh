#!/usr/bin/env bash
# Installs the local gate as the repository's pre-commit hook, so every commit runs tool/check.sh first.
#
#   tool/install_hooks.sh
#
# Why this way:
# - The hook goes into $(git rev-parse --git-common-dir)/hooks, which every worktree shares, and it execs
#   $(git rev-parse --show-toplevel)/tool/check.sh, so each worktree runs its own tracked copy of the gate.
# - A global core.hooksPath (on this machine, the english-commits dispatcher) chains to that directory after its own
#   commit-message checks, so the hook still runs.
# - `pre-commit install` refuses while a global core.hooksPath is set, so the pre-commit framework cannot do this.
# - Never edit git config: a repo-local core.hooksPath would bypass the global dispatcher and its checks.
# Safe to re-run: the same hook is written again. A different pre-commit hook is never overwritten.
set -euo pipefail
hook="$(git rev-parse --path-format=absolute --git-common-dir)/hooks/pre-commit"
want="$(
  cat <<'HOOK'
#!/bin/sh
# The local gate, installed by tool/install_hooks.sh: this checkout's own tool/check.sh (through bash, so a copy
# that lost its executable bit still runs).
exec bash "$(git rev-parse --show-toplevel)/tool/check.sh"
HOOK
)"
if [[ -e "$hook" && "$(cat "$hook")" != "$want" ]]; then
  echo "A different pre-commit hook is already installed: $hook" >&2
  echo "Fold what it does into tool/check.sh or move it aside, then run this again." >&2
  exit 1
fi
mkdir -p "$(dirname "$hook")"
printf '%s\n' "$want" >"$hook"
chmod +x "$hook"
echo "installed $hook"
