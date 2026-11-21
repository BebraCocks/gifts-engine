# Попа-Прыг

Мобильная 3D-игра для Telegram-бота @buttjump_bot. Попа сама прыгает по цилиндрам,
игрок ведёт её пальцем. 10 боссов, особые и секретные цилиндры, онлайн на двоих.

- `game/popa-pryg.html` — вся игра одним файлом (three.js с CDN). Её же публикуем как артефакт Claude.
- `worker/` — Cloudflare Worker `popa-pryg`: отдаёт игру и постер, бот (webhook), онлайн-лобби (Durable Object).
- `art/` — аватарка бота, постер 9:16 для /start, картинка 640×360 для описания бота.

## Выкладка

```bash
cd games/popa-pryg/worker
python3 build.py
CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... npx wrangler@4 deploy
curl https://popa-pryg.giftstelegram01.workers.dev/setup   # webhook, кнопка, команды, описание бота
```

Секрет воркера `TELEGRAM_BOT_TOKEN` хранится в Cloudflare, в репозиторий не попадает.
Тестовая копия: `npx wrangler@4 deploy --name popa-pryg-test`, потом удалить.

## Тестовые ссылки

`#test` — босс каждые 6 цилиндров, `#finale` — сразу к концовке, `#specials` — особые цилиндры через 6 рядов.
