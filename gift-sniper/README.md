# Gift Sniper

Юзербот на Telethon: ждёт выхода улучшений выбранных подарков и улучшает их
залпом, когда счётчик коллекции подходит к нужному номеру. Управление —
командами в «Избранном» главного аккаунта (`/help`).

- Несколько аккаунтов: `giftsniper-login acc2` добавляет аккаунт. Все аккаунты
  по очереди опрашивают счётчик (общая частота — `/rate N` запросов в секунду),
  при FloodWait аккаунт отдыхает, остальные продолжают.
- Залп: `/gift 1 3` или `/gift all 1` — подарки одной модели с любых аккаунтов
  улучшаются одновременно и занимают несколько номеров подряд. Совет:
  `/early` ≈ число подарков в залпе − 1, чтобы цель была внутри залпа.
- Цели: `/target 777 1000 1111-1115`.

## Установка (Ubuntu, от root)

```sh
curl -fsSL https://raw.githubusercontent.com/BebraCocks/gifts-engine/main/gift-sniper/install.sh | sh
giftsniper-login          # главный аккаунт
giftsniper-login acc2     # дополнительный (по желанию)
```

`giftsniper-login` спрашивает api_id/api_hash (my.telegram.org), телефон, код и
пароль 2FA, затем включает службу `giftsniper`. Сессия и настройки лежат
в `/root/.giftsniper/accounts/` (права 600), в репозиторий не попадают.

Полезное: `systemctl status giftsniper`, `journalctl -u giftsniper -f`,
`systemctl stop giftsniper`.

## Как считается номер

- Счётчик — `availability_issued` коллекционки `<Название>-1`
  (`payments.getUniqueStarGift`); следующий номер считается как счётчик + 1.
  Это предположение, документация Telegram порядок номеров не описывает.
- Если у подарка уже есть `gift_num` («Collectible number assigned to the gift,
  if already known»), номер назначен заранее и от скорости не зависит — бот
  сообщает об этом и не охотится.
- Улучшение: оплаченное заранее — `payments.upgradeStarGift`, иначе
  `getPaymentForm(inputInvoiceStarGiftUpgrade)` + `sendStarsForm`; форма
  готовится заранее, за ~30 номеров до цели.

Проверено 2026-11-28 только на имитации ответов Telegram, не на живом аккаунте.
