#!/usr/bin/env bash
# One command to ship the game: build the page, deploy the Worker, refresh the bot settings.
# Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in the environment.
# Test copy instead of the real one: ./deploy.sh test   (deletes nothing; remove it later with: npx wrangler@4 delete --name popa-pryg-test)
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
if [ "${1:-}" = "test" ]; then
  npx -y wrangler@4 deploy --name popa-pryg-test
else
  npx -y wrangler@4 deploy
  curl -fsS https://popa-pryg.giftstelegram01.workers.dev/setup; echo
fi
