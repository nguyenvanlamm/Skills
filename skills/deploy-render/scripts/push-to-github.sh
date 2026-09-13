#!/usr/bin/env bash
set -euo pipefail

SERVER_DIR=""
SLUG=""
GH_USER=""
VISIBILITY="private"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --public) VISIBILITY="public"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[ -n "$SERVER_DIR" ] || { echo "❌ --server-dir required"; exit 1; }
[ -n "$SLUG" ]       || { echo "❌ --slug required"; exit 1; }
command -v gh >/dev/null || { echo "❌ gh CLI not found — https://cli.github.com"; exit 1; }

echo "◆ Pushing to GitHub..."
cd "$SERVER_DIR"

# Determine the GitHub account from the API. `gh auth status` is human-readable
# text whose wording changes between versions, and git's user.name is a display
# name, not a repo owner.
if [ -z "$GH_USER" ]; then
  GH_USER=$(gh api user --jq .login 2>/dev/null || true)
fi
[ -n "$GH_USER" ] || { echo "❌ Cannot determine GitHub user. Provide --gh-user or run 'gh auth login'."; exit 1; }
echo "  GitHub user: $GH_USER"

REPO_NAME="${SLUG}-server"
REPO_SLUG="$GH_USER/$REPO_NAME"
REPO_URL="https://github.com/$REPO_SLUG"

# --- Local repo -----------------------------------------------------------
if [ ! -d .git ]; then
  echo "  Initialising git repository..."
  git init -q -b main
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
[ "$BRANCH" != "HEAD" ] || { echo "❌ Detached HEAD — check out a branch first."; exit 1; }

# render.yaml is written with a placeholder owner by prepare-server.sh; fill it
# in before the commit so the pushed blueprint points at the real repo.
if [ -f render.yaml ] && grep -q PLACEHOLDER_USER render.yaml; then
  sed "s/PLACEHOLDER_USER/$GH_USER/g" render.yaml > render.yaml.tmp && mv render.yaml.tmp render.yaml
  echo "  ✅ render.yaml → repo $REPO_URL"
fi
# The blueprint deploys whatever branch it names; make that the branch being pushed.
if [ -f render.yaml ] && ! grep -qE "^\s*branch:\s*$BRANCH\s*$" render.yaml; then
  sed -E "s/^(\s*branch:\s*).*/\1$BRANCH/" render.yaml > render.yaml.tmp && mv render.yaml.tmp render.yaml
  echo "  ✅ render.yaml → branch $BRANCH"
fi

# Server repos carry real secrets; never publish local env files or keys.
for pattern in ".env" ".env.*" "__pycache__/" "*.db" "*.sqlite3" "*.bak" "service-account*.json"; do
  grep -qxF "$pattern" .gitignore 2>/dev/null || echo "$pattern" >> .gitignore
done
TRACKED_SECRETS=$(git ls-files | grep -E '(^|/)\.env(\..*)?$|service-account.*\.json$' || true)
if [ -n "$TRACKED_SECRETS" ]; then
  echo "  ⚠ Secret-looking files are tracked — removing from the index:"
  echo "$TRACKED_SECRETS" | sed 's/^/     /'
  echo "$TRACKED_SECRETS" | xargs git rm --cached -q --
  echo "     If this repo was ever pushed, treat those values as leaked and rotate them."
fi

# Commit BEFORE creating the remote: `gh repo create --source=. --push` fails on
# a repository with zero commits ("src refspec main does not match any").
git add -A
if git diff --cached --quiet && git rev-parse HEAD >/dev/null 2>&1; then
  echo "  No changes to commit."
else
  git commit -q -m "chore: add Dockerfile + Render deployment config"
  echo "  ✅ Committed"
fi

# --- Remote ---------------------------------------------------------------
if gh repo view "$REPO_SLUG" >/dev/null 2>&1; then
  echo "  Repo exists: $REPO_SLUG"
  git remote get-url origin >/dev/null 2>&1 || { git remote add origin "$REPO_URL.git"; echo "  Added remote origin"; }
else
  echo "  Creating $VISIBILITY repo: $REPO_SLUG"
  gh repo create "$REPO_SLUG" "--$VISIBILITY" --source=. --remote=origin || {
    echo "❌ Failed to create the repository. Try: gh repo create $REPO_SLUG --$VISIBILITY"
    exit 1
  }
fi

# --- Push -----------------------------------------------------------------
if ! git push -u origin "$BRANCH" 2>&1; then
  echo "  Push rejected; rebasing onto the remote branch..."
  git pull --rebase origin "$BRANCH" || {
    echo "❌ Rebase failed — resolve the conflict, then: git push -u origin $BRANCH"
    exit 1
  }
  git push -u origin "$BRANCH" || { echo "❌ Push failed. Push manually: git push -u origin $BRANCH"; exit 1; }
fi

echo "✅ Pushed $BRANCH → $REPO_URL"
