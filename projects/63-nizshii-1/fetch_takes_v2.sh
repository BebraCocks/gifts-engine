#!/bin/sh
# скачивает дубли v2 из TAKES_PART1_v2.txt в voice/raw (пропускает уже скачанные)
cd "$(dirname "$0")/voice"
while read k id; do
  [ -s raw/$k.mp3 ] || curl -sf --retry 3 -o raw/$k.mp3 https://platform.r2.fish.audio/tasks/2026-11-27/$id.mp3 || echo FAIL $k
done < ../TAKES_PART1_v2.txt
ls raw | grep -c '^Q'
