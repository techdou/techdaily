#!/bin/bash
# deploy.sh — Deploy daily news via GitHub version control
# Flow: local public/ → git push → server git pull → sync to webroot
# Usage: bash scripts/deploy.sh YYYY-MM-DD
# Example: bash scripts/deploy.sh 2026-06-27
set -e

DATE="${1:?Usage: bash scripts/deploy.sh YYYY-MM-DD}"
Y="${DATE:0:4}"
M="${DATE:5:2}"
D="${DATE:8:2}"
DATE_PATH="${Y}/${M}/${D}"

REMOTE="${DEPLOY_SERVER:?Error: DEPLOY_SERVER not set (e.g. user@ip)}"
WEBROOT="${DEPLOY_PATH:?Error: DEPLOY_PATH not set (e.g. /var/www/your-domain)}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "📰 Deploying TechDaily ${DATE} via GitHub..."

# 1. Verify local files exist
if [ ! -f "$PROJECT_ROOT/public/$DATE_PATH/index.html" ]; then
    echo "  ❌ No index.html at public/$DATE_PATH/"
    exit 1
fi

# 2. Git commit + push
cd "$PROJECT_ROOT"
git add -A
if git diff --cached --quiet; then
    echo "  ℹ️  Nothing to commit (already up to date)"
else
    git commit -m "daily: deploy ${DATE}"
    echo "  ✅ Committed"
fi

git push origin main
echo "  ✅ Pushed to GitHub"

# 3. Server: git pull + sync to webroot
ssh "$REMOTE" "bash /var/www/sync-from-git.sh"

# 4. Update symlink for today
ssh "$REMOTE" "sudo ln -sfn $DATE_PATH/index.html ${WEBROOT}/index.html"

# 5. Regenerate archive
bash "$PROJECT_ROOT/scripts/gen-archive.sh"

echo ""
echo "🎉 Deployed! https://news.techdou.com/${DATE_PATH}/"
