#!/bin/bash
# switch-to-pending.sh — Switch homepage to the pending (no-update) placeholder.
#
# Called by the early-morning agent cron (e.g. 00:00 Asia/Shanghai) so that
# after midnight the root "/" shows the "today's edition is coming" page until
# the daily pipeline publishes and repoints the symlink to that day's report.
#
# The pending page (public/pending.html) is already on the server, synced via
# the normal git flow, so all we do is flip /var/www/.../index.html → pending.html.
# pipeline.py's deploy_no_update() does the exact same switch for RSS-failure cases.
#
# Usage: bash scripts/switch-to-pending.sh

set -e

REMOTE="${DEPLOY_SERVER:?Error: DEPLOY_SERVER not set}"
WEBROOT="${DEPLOY_PATH:?Error: DEPLOY_PATH not set}"

echo "🔄 Switching homepage to pending (no-update)..."
ssh "$REMOTE" "sudo ln -sfn pending.html ${WEBROOT}/index.html"
echo "✅ Homepage → pending.html  (https://news.techdou.com)"
