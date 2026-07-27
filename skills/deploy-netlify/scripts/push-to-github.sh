#!/usr/bin/env bash
set -euo pipefail

CLIENT_DIR=""
SLUG=""
GH_USER=""
VISIBILITY="private"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --public) VISIBILITY="public"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[ -n "$CLIENT_DIR" ] || { echo "❌ --client-dir required"; exit 1; }
[ -n "$SLUG" ]       || { echo "❌ --slug required"; exit 1; }
command -v gh >/dev/null || { echo "❌ gh CLI not found — https://cli.github.com"; exit 1; }

echo "◆ Pushing to GitHub..."
cd "$CLIENT_DIR"

# --- GitHub account -------------------------------------------------------
# Ask the API, not the CLI's human-readable status text: that wording has
# changed between gh versions, and git's user.name is a display name
# ("Nguyen Van Lam"), never a valid repo owner.
if [ -z "$GH_USER" ]; then
  GH_USER=$(gh api user --jq .login 2>/dev/null || true)
fi
if [ -z "$GH_USER" ]; then
  echo "❌ Cannot determine the GitHub account. Run 'gh auth login', or pass --gh-user."
  exit 1
fi
echo "  Account: $GH_USER"

REPO_NAME="${SLUG}-client"
REPO_SLUG="$GH_USER/$REPO_NAME"

# --- Local repo -----------------------------------------------------------
if [ ! -d .git ]; then
  echo "  Initialising git repository..."
  git init -q -b main
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
[ "$BRANCH" != "HEAD" ] || { echo "❌ Detached HEAD — check out a branch first."; exit 1; }

# Never publish local env files. Vite bakes VITE_* into the bundle at build
# time, so committing them adds exposure without adding function.
for pattern in ".env" ".env.*" "node_modules/" "dist/"; do
  grep -qxF "$pattern" .gitignore 2>/dev/null || echo "$pattern" >> .gitignore
done
if git ls-files --error-unmatch .env .env.production >/dev/null 2>&1; then
  echo "  ⚠ .env files are already tracked — removing them from the index"
  git rm --cached -q .env .env.production 2>/dev/null || true
fi

git add -A
if git diff --cached --quiet; then
  echo "  Nothing to commit"
else
  git commit -q -m "chore: add Netlify deployment config"
  echo "  ✅ Committed"
fi

# --- Remote ---------------------------------------------------------------
if gh repo view "$REPO_SLUG" >/dev/null 2>&1; then
  echo "  Repo exists: $REPO_SLUG"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$REPO_SLUG.git"
    echo "  Added remote origin"
  fi
else
  echo "  Creating $VISIBILITY repo: $REPO_SLUG"
  gh repo create "$REPO_SLUG" "--$VISIBILITY" --source=. --remote=origin || {
    echo "❌ Failed to create the repository."
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
  git push -u origin "$BRANCH" || {
    echo "❌ Push failed. Push manually: git push -u origin $BRANCH"
    exit 1
  }
fi

echo "✅ Pushed $BRANCH → https://github.com/$REPO_SLUG"
