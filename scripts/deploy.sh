#!/bin/bash
# deploy.sh — Deploy daily news to server
# Usage: bash scripts/deploy.sh YYYY-MM-DD
# Example: bash scripts/deploy.sh 2026-06-27
set -e

DATE="${1:?Usage: bash scripts/deploy.sh YYYY-MM-DD}"
Y="${DATE:0:4}"
M="${DATE:5:2}"
D="${DATE:8:2}"
DATE_PATH="${Y}/${M}/${D}"

REMOTE="ubuntu@43.153.24.30"
WEBROOT="/var/www/news.techdou.com"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "📰 Deploying TechDaily ${DATE}..."

# 1. Ensure server directory exists
ssh "$REMOTE" "sudo mkdir -p $WEBROOT/$DATE_PATH"

# 2. Upload HTML
if [ -f "$PROJECT_ROOT/public/$DATE_PATH/index.html" ]; then
    scp "$PROJECT_ROOT/public/$DATE_PATH/index.html" "$REMOTE:/tmp/td-index.html"
    ssh "$REMOTE" "sudo mv /tmp/td-index.html $WEBROOT/$DATE_PATH/index.html"
    echo "  ✅ HTML uploaded"
else
    echo "  ❌ No index.html found at public/$DATE_PATH/"
    exit 1
fi

# 3. Upload audio (if exists)
if [ -f "$PROJECT_ROOT/public/$DATE_PATH/audio.mp3" ]; then
    scp "$PROJECT_ROOT/public/$DATE_PATH/audio.mp3" "$REMOTE:/tmp/td-audio.mp3"
    ssh "$REMOTE" "sudo mv /tmp/td-audio.mp3 $WEBROOT/$DATE_PATH/audio.mp3"
    echo "  ✅ Audio uploaded"
fi

# 4. Upload static assets (logo, favicon, pet, etc.)
rsync -az --delete \
    "$PROJECT_ROOT/public/assets/" \
    "$REMOTE:/tmp/td-assets/"
ssh "$REMOTE" "sudo rsync -a /tmp/td-assets/ $WEBROOT/assets/ && rm -rf /tmp/td-assets"

scp "$PROJECT_ROOT/public/pet.html" "$REMOTE:/tmp/td-pet.html" 2>/dev/null && \
    ssh "$REMOTE" "sudo mv /tmp/td-pet.html $WEBROOT/pet.html" || true
scp "$PROJECT_ROOT/public/pet.js" "$REMOTE:/tmp/td-pet.js" 2>/dev/null && \
    ssh "$REMOTE" "sudo mv /tmp/td-pet.js $WEBROOT/pet.js" || true
scp "$PROJECT_ROOT/public/404.html" "$REMOTE:/tmp/td-404.html" 2>/dev/null && \
    ssh "$REMOTE" "sudo mv /tmp/td-404.html $WEBROOT/404.html" || true

echo "  ✅ Static assets synced"

# 5. Set permissions
ssh "$REMOTE" "sudo chown -R www-data:www-data $WEBROOT/"

# 6. Update symlink for today
ssh "$REMOTE" "sudo ln -sfn $DATE_PATH/index.html $WEBROOT/index.html"
echo "  ✅ Symlink updated → $DATE_PATH"

# 7. Regenerate archive
bash "$PROJECT_ROOT/scripts/gen-archive.sh"

echo ""
echo "🎉 Deployed! https://news.techdou.com/${DATE_PATH}/"
