#!/usr/bin/env bash
set -euo pipefail

CLIENT_DIR=""
SLUG=""
GH_USER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$CLIENT_DIR" ]; then echo "❌ --client-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi

echo "◆ Pushing to GitHub..."
cd "$CLIENT_DIR"

# Determine GitHub user
if [ -z "$GH_USER" ]; then
  GH_USER=$(gh auth status 2>&1 | grep -oP 'Logged in to github\.com as \K\S+' || true)
  if [ -z "$GH_USER" ]; then
    GH_USER=$(git config --global user.name 2>/dev/null || echo "")
  fi
  if [ -z "$GH_USER" ]; then
    echo "❌ Cannot determine GitHub user. Provide --gh-user or run 'gh auth login'."
    exit 1
  fi
fi
echo "  GitHub user: $GH_USER"

REPO_NAME="${SLUG}-client"
REPO_URL="https://github.com/$GH_USER/$REPO_NAME"

# Create repo if needed
if gh repo view "$GH_USER/$REPO_NAME" &>/dev/null 2>&1; then
  echo "  Repo $GH_USER/$REPO_NAME already exists"
else
  echo "  Creating repo: $GH_USER/$REPO_NAME..."
  gh repo create "$GH_USER/$REPO_NAME" --private --push --source=. 2>&1 || {
    echo "❌ Failed to create repo."
    exit 1
  }
  echo "  ✅ Repo created: $REPO_URL"
fi

# Set remote
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
  git commit -m "Add Netlify deployment config"
  echo "  ✅ Committed"
fi

git push -u origin main 2>&1 || {
  echo "  Pulling remote changes..."
  git pull --rebase origin main 2>/dev/null || true
  git push -u origin main 2>&1 || {
    echo "❌ Push failed. Push manually: git push -u origin main"
    exit 1
  }
}

echo "✅ Push complete: $REPO_URL"
