#!/usr/bin/env bash
# Local gate (no hosted CI by owner rule): format, analyze, test. The pre-commit hook runs it in every worktree
# (tool/install_hooks.sh); run it by hand the same way.
#
#   tool/check.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
# Git exports these to hooks. Flutter and Dart check their own SDK with git, and in a worktree these variables point
# those checks at the game repo instead: Flutter reports version 0.0.0-unknown, rebuilds its tool, and pub resolution
# fails on the SDK constraint. Unset them before any SDK call.
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_COMMON_DIR GIT_OBJECT_DIRECTORY \
  GIT_ALTERNATE_OBJECT_DIRECTORIES

dirs=()
for d in lib test tool; do
  if [[ -d "$d" ]]; then dirs+=("$d"); fi
done
echo '== format'
dart format --output=none --set-exit-if-changed "${dirs[@]}"
echo '== analyze'
flutter analyze
echo '== test'
flutter test
echo '== ok'
