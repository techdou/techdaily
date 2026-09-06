#!/usr/bin/env python3
"""Run TechDaily pipeline with a locally pre-fetched RSS file.

Bypasses fetch_rss()'s direct network fetch. Use when the Mac cannot reach
daily.juya.uk directly (proxy/down network) and the RSS was relayed via the
Tencent server (see fetch-rss-via-server.sh). Deployment is always skipped
here; pair with manual-deploy.sh.

Usage:
    python3 scripts/run-with-local-rss.py /tmp/rss-fresh.xml --date 2026-09-06
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rss_file', help='local RSS XML path (server-relayed)')
    parser.add_argument('--date', help='target date YYYY-MM-DD')
    parser.add_argument('--skip-tts', action='store_true')
    args = parser.parse_args()

    rss_path = Path(args.rss_file)
    if not rss_path.exists():
        print(f"❌ RSS file not found: {rss_path}")
        sys.exit(2)

    def local_fetch(url=None):
        data = rss_path.read_bytes()
        print(f"   ✅ Loaded {len(data)} bytes from {rss_path} (server relay)")
        return data

    pipeline.fetch_rss = local_fetch
    result = pipeline.run_pipeline(
        target_date=args.date,
        skip_tts=args.skip_tts,
        skip_deploy=True,  # GitHub push unavailable during outage; use manual-deploy.sh
    )
    sys.exit(0 if result else 1)


if __name__ == '__main__':
    main()
