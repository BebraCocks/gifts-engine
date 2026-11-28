"""Вход в Telegram-аккаунт и (пере)запуск бота как службы.

giftsniper-login         — главный аккаунт (в его «Избранном» команды бота)
giftsniper-login acc2    — дополнительный аккаунт с именем acc2

Спрашивает api_id и api_hash (my.telegram.org, один раз на все аккаунты),
номер телефона, код и пароль двухэтапной проверки. Всё вводится только здесь.
"""

import asyncio
import getpass
import re
import subprocess
import sys

from bot import ACCOUNTS, DATA, MAIN, load_config, make_client, \
    migrate_old_session, save_config


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else MAIN
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name):
        raise SystemExit("Имя аккаунта: латиница, цифры, - и _, например acc2")
    DATA.mkdir(parents=True, exist_ok=True)
    DATA.chmod(0o700)
    ACCOUNTS.mkdir(parents=True, exist_ok=True)
    migrate_old_session()
    cfg = load_config()
    if not cfg.get("api_id"):
        print("Ключи берутся на https://my.telegram.org → API development tools")
        cfg["api_id"] = int(input("api_id: ").strip())
        cfg["api_hash"] = input("api_hash: ").strip()
        save_config(cfg)

    print(f"Вход в аккаунт «{name}»")
    client = make_client(name, cfg)
    await client.start(
        phone=lambda: input("Номер телефона (+7...): ").strip(),
        code_callback=lambda: input("Код из Telegram: ").strip(),
        password=lambda: getpass.getpass("Пароль двухэтапной проверки "
                                         "(если нет — Enter): "))
    me = await client.get_me()
    print(f"\nВход выполнен: {me.first_name} (@{me.username or '-'})")
    await client.disconnect()
    for p in ACCOUNTS.iterdir():
        p.chmod(0o600)

    subprocess.run(["systemctl", "enable", "giftsniper"], check=False)
    subprocess.run(["systemctl", "restart", "giftsniper"], check=False)
    print("Бот (пере)запущен. Откройте «Избранное» главного аккаунта в Telegram. "
          "Окно терминала можно закрыть.")


if __name__ == "__main__":
    asyncio.run(main())
