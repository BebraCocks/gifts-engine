"""Первый вход в Telegram и запуск бота как службы.

Спрашивает api_id и api_hash (my.telegram.org), номер телефона, код
и пароль двухэтапной проверки. Всё вводится только здесь, на сервере.
"""

import asyncio
import getpass
import subprocess

from telethon import TelegramClient

from bot import DATA, SESSION, load_config, save_config


async def main():
    DATA.mkdir(parents=True, exist_ok=True)
    DATA.chmod(0o700)
    cfg = load_config()
    if not cfg.get("api_id"):
        print("Ключи берутся на https://my.telegram.org → API development tools")
        cfg["api_id"] = int(input("api_id: ").strip())
        cfg["api_hash"] = input("api_hash: ").strip()
        save_config(cfg)

    client = TelegramClient(SESSION, cfg["api_id"], cfg["api_hash"],
                            device_model="Gift Sniper", system_version="server")
    await client.start(
        phone=lambda: input("Номер телефона (+7...): ").strip(),
        code_callback=lambda: input("Код из Telegram: ").strip(),
        password=lambda: getpass.getpass("Пароль двухэтапной проверки "
                                         "(если нет — Enter): "))
    me = await client.get_me()
    print(f"\nВход выполнен: {me.first_name} (@{me.username or '-'})")
    await client.disconnect()
    for p in DATA.iterdir():
        p.chmod(0o600)

    subprocess.run(["systemctl", "enable", "--now", "giftsniper"], check=False)
    subprocess.run(["systemctl", "restart", "giftsniper"], check=False)
    print("Бот запущен. Откройте «Избранное» в Telegram — там будет сообщение "
          "от бота. Окно терминала можно закрыть.")


if __name__ == "__main__":
    asyncio.run(main())
