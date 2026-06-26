#!/bin/bash
# deploy-no-update.sh — Deploy no-update placeholder for a specific date
# Usage: ./deploy-no-update.sh [YYYY-MM-DD]
# If no date given, uses today's date.

set -euo pipefail

# Help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $(basename "$0") [YYYY-MM-DD]"
    echo "Deploy no-update placeholder page to news.techdou.com"
    echo ""
    echo "Options:"
    echo "  YYYY-MM-DD  Target date (default: today)"
    echo ""
    echo "Environment:"
    echo "  SERVER_USER  SSH user (default: ubuntu)"
    echo "  SERVER_HOST  SSH host (default: 43.153.24.30)"
    echo "  DOMAIN       Base domain (default: techdou.com)"
    echo "  SUBDOMAIN    Subdomain (default: news)"
    exit 0
fi

# Config
SERVER_USER="${SERVER_USER:-ubuntu}"
SERVER_HOST="${SERVER_HOST:-43.153.24.30}"
DOMAIN="${DOMAIN:-techdou.com}"
SUBDOMAIN="${SUBDOMAIN:-news}"
REMOTE_DIR="/var/www/${SUBDOMAIN}.${DOMAIN}"

# Date
TARGET_DATE="${1:-$(date +%Y-%m-%d)}"
Y="${TARGET_DATE:0:4}"
M="${TARGET_DATE:5:2}"
D="${TARGET_DATE:8:2}"
DATE_PATH="${Y}/${M}/${D}"

echo "📝 Deploying no-update placeholder for ${TARGET_DATE}..."

# Ensure no-update.html exists locally
NO_UPDATE_LOCAL="${HOME}/.openclaw/skills/daily-news/assets/no-update.html"
if [[ ! -f "${NO_UPDATE_LOCAL}" ]]; then
    echo "   ❌ no-update.html not found at ${NO_UPDATE_LOCAL}"
    exit 1
fi

# Copy to server (overwrite if exists)
scp -q "${NO_UPDATE_LOCAL}" "${SERVER_USER}@${SERVER_HOST}:/tmp/no-update.html"

# Deploy on server
ssh "${SERVER_USER}@${SERVER_HOST}" "
    sudo mkdir -p ${REMOTE_DIR}/${DATE_PATH} && \
    sudo cp /tmp/no-update.html ${REMOTE_DIR}/${DATE_PATH}/index.html && \
    sudo chown -R www-data:www-data ${REMOTE_DIR}/${DATE_PATH}/ && \
    sudo ln -sfn ${DATE_PATH}/index.html ${REMOTE_DIR}/index.html && \
    echo '✅ Done'
"

echo "   ✅ No-update page deployed: ${REMOTE_DIR}/${DATE_PATH}/"
echo "   🔗 https://${SUBDOMAIN}.${DOMAIN}"
