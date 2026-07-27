#!/usr/bin/env bash
set -euo pipefail

SERVER_DIR=""
SLUG=""
GH_USER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$SERVER_DIR" ]; then echo "❌ --server-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi

echo "◆ Pushing to GitHub..."

cd "$SERVER_DIR"

# Determine the GitHub account from the API. `gh auth status` is human-readable
# text whose wording changes between versions, and git's user.name is a display
# name, not a repo owner.
if [ -z "$GH_USER" ]; then
  GH_USER=$(gh api user --jq .login 2>/dev/null || true)
fi
if [ -z "$GH_USER" ]; then
  echo "❌ Cannot determine GitHub user. Provide --gh-user or run 'gh auth login'."
  exit 1
fi
echo "  GitHub user: $GH_USER"

# A repo must exist locally before `gh repo create --source=.` can use it.
if [ ! -d .git ]; then
  echo "  Initialising git repository..."
  git init -q -b main
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
[ "$BRANCH" != "HEAD" ] || { echo "❌ Detached HEAD — check out a branch first."; exit 1; }

# Server repos carry real secrets; never publish local env files.
for pattern in ".env" ".env.*" "__pycache__/" "*.db" "*.sqlite3"; do
  grep -qxF "$pattern" .gitignore 2>/dev/null || echo "$pattern" >> .gitignore
done
git ls-files --error-unmatch .env >/dev/null 2>&1 && {
  echo "  ⚠ .env is tracked — removing from the index"
  git rm --cached -q .env 2>/dev/null || true
} || true

REPO_NAME="${SLUG}-server"
REPO_URL="https://github.com/$GH_USER/$REPO_NAME"

# Create GitHub repo if needed
if gh repo view "$GH_USER/$REPO_NAME" &>/dev/null 2>&1; then
  echo "  Repo $GH_USER/$REPO_NAME already exists on GitHub"
else
  echo "  Creating repo: $GH_USER/$REPO_NAME..."
  gh repo create "$GH_USER/$REPO_NAME" --private --source=. --remote=origin --push 2>&1 || {
    gh repo create "$GH_USER/$REPO_NAME" --private --push 2>&1 || {
      echo "❌ Failed to create repo. Try: gh repo create $GH_USER/$REPO_NAME --private"
      exit 1
    }
  }
  echo "  ✅ Repo created: $REPO_URL"
fi

# Update render.yaml with correct GitHub user
if [ -f "render.yaml" ]; then
  # -i with no argument is GNU-only; BSD/macOS sed needs an explicit suffix.
  sed "s/PLACEHOLDER_USER/$GH_USER/g" render.yaml > render.yaml.tmp && mv render.yaml.tmp render.yaml
  echo "  ✅ Updated render.yaml with user $GH_USER"
fi

# Set up remote
if git remote get-url origin &>/dev/null 2>&1; then
  echo "  Remote origin already set: $(git remote get-url origin)"
else
  git remote add origin "$REPO_URL"
  echo "  Added remote: $REPO_URL"
fi

# Stage, commit, push
git add -A

if git diff --cached --quiet; then
  echo "  No changes to commit."
else
  git commit -m "Add Dockerfile + Render deployment config"
  echo "  ✅ Committed"
fi

echo "  Pushing..."
git push -u origin "$BRANCH" 2>&1 || {
  echo "  Pulling remote changes first..."
  git pull --rebase origin main 2>/dev/null || true
  git push -u origin "$BRANCH" 2>&1 || {
    echo "❌ Push failed. Push manually: git push -u origin $BRANCH"
    exit 1
  }
}

echo "✅ Push complete: $REPO_URL"
