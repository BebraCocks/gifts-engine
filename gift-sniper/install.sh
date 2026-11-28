#!/bin/sh
# Установка Gift Sniper на сервер Ubuntu (запускать от root).
# curl -fsSL https://raw.githubusercontent.com/BebraCocks/gifts-engine/main/gift-sniper/install.sh | sh
set -e
BASE=https://raw.githubusercontent.com/BebraCocks/gifts-engine/main/gift-sniper
DIR=/opt/giftsniper

echo "== Ставлю Python…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv curl >/dev/null

echo "== Скачиваю бота…"
mkdir -p "$DIR"
for f in bot.py login.py panel.py panel.html panel-setup.sh requirements.txt giftsniper.service; do
  curl -fsSL "$BASE/$f" -o "$DIR/$f"
done
mkdir -p "$DIR/sounds"
for v in plan_add plan_count slug early rate idle bwin brate; do
  curl -fsSL "$BASE/sounds/$v.mp3" -o "$DIR/sounds/$v.mp3"
done

echo "== Ставлю библиотеки…"
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install -q --upgrade pip
"$DIR/venv/bin/pip" install -q -r "$DIR/requirements.txt"
"$DIR/venv/bin/pip" install -q cryptg 2>/dev/null || echo "(cryptg не встал — не страшно)"

cp "$DIR/giftsniper.service" /etc/systemd/system/giftsniper.service
systemctl daemon-reload

cat > /usr/local/bin/giftsniper-login <<EOF
#!/bin/sh
cd $DIR && exec $DIR/venv/bin/python login.py "\$@"
EOF
chmod +x /usr/local/bin/giftsniper-login
cp "$DIR/panel-setup.sh" /usr/local/bin/giftsniper-panel
chmod +x /usr/local/bin/giftsniper-panel

if ls /root/.giftsniper/accounts/*.session >/dev/null 2>&1; then
  systemctl restart giftsniper
  echo
  echo "Готово. Бот обновлён и перезапущен."
else
  echo
  echo "Готово. Теперь введите:  giftsniper-login"
fi
