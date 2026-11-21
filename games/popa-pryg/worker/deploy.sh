#!/usr/bin/env bash
# One command to ship the game: build the page, deploy the Worker, refresh the bot settings.
# Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in the environment.
# Test copy instead of the real one: ./deploy.sh test   (deletes nothing; remove it later with: npx wrangler@4 delete --name popa-pryg-test)
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
# music lives in KV (binding MEDIA); upload a track only when it changed since the last upload
mkdir -p .uploaded
for f in assets/music/*.mp3; do
  [ -e "$f" ] || continue
  sum=$(sha1sum "$f" | cut -d' ' -f1); mark=".uploaded/$(basename "$f").sha1"
  if [ "$(cat "$mark" 2>/dev/null)" != "$sum" ]; then
    npx -y wrangler@4 kv key put --binding MEDIA --remote "music/$(basename "$f")" --path "$f" && echo "$sum" > "$mark"
  fi
done
if [ "${1:-}" = "test" ]; then
  npx -y wrangler@4 deploy --name popa-pryg-test
else
  npx -y wrangler@4 deploy
  curl -fsS https://popa-pryg.giftstelegram01.workers.dev/setup; echo
fi
