"""Sample Telegram-chat frames for the author's review: build/review/tg_*.png (1080×1920)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chars as C  # noqa: E402
import tg  # noqa: E402
from tg import blocked, draft, gift, msg, note, status, typing  # noqa: E402

OUT = HERE / 'build' / 'review'
W, H = 1080, 1920

AV_DIMA = tg.head_avatar(C.head('dima', smile=0.6), bg=(150, 200, 160))
AV_KATYA = tg.head_avatar(C.head('katya', smile=0.6), bg=(240, 190, 190))
AV_ALEX = tg.head_avatar(C.head('alex', smile=0.7, open_=0.35, teeth=1.0), bg=(150, 180, 230))
AV_UNKNOWN = tg.circle(C.avatar('unknown', 240), 240)

CHATS = {
    'dima': (7.6, dict(theme='day', name='Дима', status='в сети', avatar=AV_DIMA, clock='16:05', events=[
        msg(0.0, 'out', 'Привет! Видел у тебя календарь в профиле 🔥', '16:02'),
        msg(1.0, 'in', 'Привет) да, мама подарила', '16:03'),
        msg(2.0, 'out', 'Слушай, скинь на 5 минут? Скрин для канала сделаю и сразу верну 🙏', '16:03'),
        typing(3.0, 4.0),
        msg(4.0, 'in', 'Ну ладно… только правда верни', '16:04'),
        gift(5.0, 'in', 'Desk Calendar', 'Sunshine', 'Sky Blue', 'Дима отправил вам подарок'),
        msg(6.4, 'out', 'Спасибо, лошара 😂', '16:05'),
        blocked(7.2), note(7.2, 'Вы заблокировали пользователя'),
    ])),
    'katya_draft': (5.2, dict(theme='night', name='Катя', status='в сети', avatar=AV_KATYA, clock='23:41', events=[
        msg(0.0, 'in', 'Жду не дождусь субботы 🥰', '23:12'),
        msg(0.6, 'out', 'Я тоже, Кать ❤️', '23:13'),
        draft(2.0, 6.0, 'Кать, прости пожалуйста, но я не смогу приехать на свидание…'),
    ])),
    'katya_gifts': (9.0, dict(theme='night', name='Катя', status='в сети', avatar=AV_KATYA, clock='23:58', events=[
        msg(0.0, 'in', 'Блин, чего же ты раньше молчал?! Сейчас помогу, чем смогу!', '23:52'),
        gift(1.5, 'in', 'Plush Pepe', 'Tropical', 'Pure Gold', 'Катя отправила вам подарок'),
        gift(3.0, 'in', 'Resistance Dog', 'Caesar', 'Emerald', 'Катя отправила вам подарок'),
        gift(4.5, 'in', 'Heart Locket', 'Royal Flush', 'Raspberry', 'Катя отправила вам подарок'),
        msg(6.0, 'in', 'Вот, держи. Это всё, что у меня было ❤️ Надеюсь, тебе поможет', '23:58'),
    ])),
    'final': (2.0, dict(theme='night', name='Неизвестный', status='был(а) недавно', avatar=AV_UNKNOWN,
                        clock='02:13', events=[msg(0.5, 'in', 'Зря ты это сделал, Петя.', '02:13')])),
}


def backdrop(theme):
    im = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(im)
    a, b = ((60, 52, 84), (24, 20, 36)) if theme == 'night' else ((236, 226, 208), (196, 180, 160))
    for y in range(H):
        k = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)) + (255,))
    return im


def frame(key):
    t, chat = CHATS[key]
    im = backdrop(chat['theme'])
    dev = tg.phone(tg.chat_screen(t, chat))
    sh = Image.new('RGBA', dev.size, (0, 0, 0, 0))
    sh.putalpha(dev.getchannel('A').point(lambda v: int(v * 0.5)))
    sh = sh.filter(ImageFilter.GaussianBlur(26))
    x, y = (W - dev.width) // 2, (H - dev.height) // 2
    im.alpha_composite(sh, (x + 10, y + 24))
    im.alpha_composite(dev, (x, y))
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for k in (sys.argv[1:] or CHATS):
        p = OUT / f'tg_{k}.png'
        frame(k).convert('RGB').save(p)
        print(p)


if __name__ == '__main__':
    main()
