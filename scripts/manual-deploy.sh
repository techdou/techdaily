#!/bin/bash
# manual-deploy.sh — Deploy TechDaily when GitHub push is unavailable (network outage fallback)
#
# Equivalent to pipeline.py's deploy_site() but replaces `git push → server git pull`
# with direct rsync over Tailscale. GitHub sync is deferred: commits stay local and
# go out with the next successful push (e.g. next day's normal pipeline run).
#
# Usage: bash scripts/manual-deploy.sh YYYY-MM-DD
set -e

DATE="${1:?Usage: bash scripts/manual-deploy.sh YYYY-MM-DD}"
Y="${DATE:0:4}"; M="${DATE:5:2}"; D="${DATE:8:2}"
DATE_PATH="$Y/$M/$D"

REMOTE="${DEPLOY_SERVER:-ubuntu@100.86.23.97}"
WEBROOT="${DEPLOY_PATH:-/var/www/news.techdou.com}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Verify outputs exist
[ -f "$PROJECT_ROOT/output/$DATE.html" ] || { echo "❌ output/$DATE.html missing"; exit 1; }

# 2. Copy into public/
mkdir -p "$PROJECT_ROOT/public/$DATE_PATH"
cp "$PROJECT_ROOT/output/$DATE.html" "$PROJECT_ROOT/public/$DATE_PATH/index.html"
echo "✅ HTML → public/$DATE_PATH/index.html"
if [ -f "$PROJECT_ROOT/output/${DATE}_broadcast.mp3" ]; then
    cp "$PROJECT_ROOT/output/${DATE}_broadcast.mp3" "$PROJECT_ROOT/public/$DATE_PATH/audio.mp3"
    echo "✅ Audio → public/$DATE_PATH/audio.mp3"
fi

# 3. Local git commit (push deferred until network recovers)
cd "$PROJECT_ROOT"
git add -A
if git diff --cached --quiet; then
    echo "ℹ️  Nothing new to commit"
else
    git commit -m "daily: deploy $DATE"
    echo "✅ Committed locally (push deferred)"
fi

# 4. rsync to server webroot (⚠️ --no-perms/owner/group per deploy.sh warning)
rsync -a --no-perms --no-owner --no-group \
    "$PROJECT_ROOT/public/$DATE_PATH/" "$REMOTE:$WEBROOT/$DATE_PATH/"
echo "✅ rsync → $REMOTE:$WEBROOT/$DATE_PATH/"

# 5. Fix ownership/permissions on server + switch homepage symlink to today
ssh "$REMOTE" "
    sudo chown -R www-data:www-data $WEBROOT/$DATE_PATH
    sudo find $WEBROOT/$DATE_PATH -type d -exec chmod 755 {} \;
    sudo find $WEBROOT/$DATE_PATH -type f -exec chmod 644 {} \;
    sudo ln -sfn $DATE_PATH/index.html $WEBROOT/index.html
    echo '✅ permissions + symlink updated'
"

# 6. Regenerate archive page (also scp's archive.html back into public/)
bash "$PROJECT_ROOT/scripts/gen-archive.sh"

# 7. Verify from the server itself
ssh "$REMOTE" "curl -s -o /dev/null -w 'today page: %{http_code}\n' -H 'Host: news.techdou.com' http://127.0.0.1/$DATE_PATH/; curl -s -o /dev/null -w 'homepage:   %{http_code}\n' -H 'Host: news.techdou.com' http://127.0.0.1/"

echo ""
echo "🎉 Manually deployed! https://news.techdou.com/$DATE_PATH/"
