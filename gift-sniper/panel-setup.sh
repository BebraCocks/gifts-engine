#!/bin/bash
# Подключение панели: токен бота от @BotFather + HTTPS-адрес для мини-аппа.
set -e
DIR=/opt/giftsniper

printf "Токен бота от @BotFather (при вводе не виден): "
read -rs TOKEN; echo
case "$TOKEN" in
  *:*) ;;
  *) echo "Это не похоже на токен (нужна строка вида 123456:ABC...)"; exit 1 ;;
esac

IP=$(curl -fsS4 https://api.ipify.org 2>/dev/null || hostname -I | tr ' ' '\n' | grep -m1 -E '^[0-9.]+$')
DOMAIN="$(echo "$IP" | tr . -).sslip.io"
echo "Адрес панели: https://$DOMAIN"

cd "$DIR"
GS_TOKEN="$TOKEN" GS_DOMAIN="$DOMAIN" "$DIR/venv/bin/python" -c '
import os, bot
c = bot.load_config()
c["panel"] = {"token": os.environ["GS_TOKEN"], "domain": os.environ["GS_DOMAIN"]}
bot.save_config(c)'

echo "== Ставлю Caddy (HTTPS-сертификат)…"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq caddy >/dev/null
cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
	reverse_proxy 127.0.0.1:8088
}
CADDY
if command -v ufw >/dev/null && ufw status | grep -q active; then
  ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
fi
systemctl enable -q caddy
systemctl restart caddy
systemctl restart giftsniper

echo
echo "Готово. Откройте своего бота в Telegram, нажмите «Запустить» (/start),"
echo "затем кнопку «Панель» слева от поля ввода. Сертификат может"
echo "выпускаться 1–2 минуты — если панель не открылась, подождите."
