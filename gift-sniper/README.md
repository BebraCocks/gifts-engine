# Gift Sniper

Юзербот на Telethon: ждёт выхода улучшений выбранного подарка и улучшает его,
когда счётчик коллекции подходит к нужному номеру. Управление — командами
в «Избранном» Telegram (`/help`).

## Установка (Ubuntu, от root)

```sh
curl -fsSL https://raw.githubusercontent.com/BebraCocks/gifts-engine/main/gift-sniper/install.sh | sh
giftsniper-login
```

`giftsniper-login` спрашивает api_id/api_hash (my.telegram.org), телефон, код и
пароль 2FA, затем включает службу `giftsniper`. Сессия и настройки лежат
в `/root/.giftsniper/` (права 600), в репозиторий не попадают.

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
