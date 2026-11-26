"""Telegram-style chat card drawn in code (64-missed-aizen).

Grayscale UI to match the manga look; only Missed's avatar (and his name) carry color.
    img = chat_card([("in", "Да"), ("out", "Ты щедрый?")], n_visible=2)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONT_DIR = ROOT / "input" / "fonts" / "SF-Pro-Text"
SS = 2  # supersampling

# Telegram dark layout, desaturated
BG = (24, 24, 26)
HEADER = (36, 36, 39)
IN_BUBBLE = (122, 62, 78)  # Missed's bubbles: the colored ones
OUT_BUBBLE = (236, 236, 236)
IN_TEXT = (245, 245, 245)
OUT_TEXT = (20, 20, 20)
META_IN = (215, 170, 180)
META_OUT = (110, 110, 110)
MISSED_NAME = (255, 170, 170)  # the only accent color besides the avatar


def _font(weight, px):
    return ImageFont.truetype(str(FONT_DIR / f"SF-Pro-Text-{weight}.otf"), px * SS)


def missed_avatar(d):
    """Round crop of the author's Missed picture, d px (already supersampled)."""
    src = Image.open(HERE / "refs" / "missed.jpg").convert("RGB")
    cx, cy, r = 330, 290, 215
    face = src.crop((cx - r, cy - r, cx + r, cy + r)).resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    out = Image.new("RGBA", (d, d))
    out.paste(face, (0, 0), mask)
    return out


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def chat_card(messages, n_visible=None, width=960, height=1180, times=None):
    """messages: [("in"|"out", text)]. n_visible: how many are shown (for step-by-step reveal)."""
    W, H = width * SS, height * SS
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    rad = 40 * SS
    # header
    hh = 150 * SS
    d.rectangle((0, 0, W, hh), fill=HEADER)
    d.line((40 * SS, hh // 2, 60 * SS, hh // 2 - 20 * SS), fill=(200, 200, 200), width=6 * SS)
    d.line((40 * SS, hh // 2, 60 * SS, hh // 2 + 20 * SS), fill=(200, 200, 200), width=6 * SS)
    av = 100 * SS
    img.alpha_composite(missed_avatar(av), (100 * SS, (hh - av) // 2))
    d.text((225 * SS, 30 * SS), "Мисед", font=_font("Semibold", 40), fill=MISSED_NAME)
    d.text((225 * SS, 82 * SS), "в сети", font=_font("Regular", 30), fill=(150, 150, 155))
    head = img.crop((0, 0, W, hh))

    msgs = messages if n_visible is None else messages[:n_visible]
    f = _font("Regular", 44)
    fm = _font("Regular", 24)
    pad_x, pad_y, gap = 34 * SS, 22 * SS, 18 * SS
    max_w = int(W * 0.68)
    blocks = []
    for i, (side, text) in enumerate(msgs):
        lines = _wrap(d, text, f, max_w - 2 * pad_x)
        lh = 58 * SS
        tw = max(d.textlength(l, font=f) for l in lines)
        meta = (times[i] if times else "21:0%d" % (i % 10)) + (" ✓✓" if side == "out" else "")
        mw = d.textlength(meta, font=fm)
        bw = int(max(tw, 0) + 2 * pad_x + mw + 20 * SS)
        bh = int(len(lines) * lh + 2 * pad_y)
        blocks.append((side, lines, meta, bw, bh, lh))
    # stack from the bottom (newest at the bottom, like Telegram)
    y = H - 40 * SS - sum(b[4] + gap for b in blocks)
    for side, lines, meta, bw, bh, lh in blocks:
        x = W - 56 * SS - bw if side == "out" else 56 * SS
        col = OUT_BUBBLE if side == "out" else IN_BUBBLE
        d.rounded_rectangle((x, y, x + bw, y + bh), radius=rad, fill=col)
        # tail
        if side == "out":
            tx = x + bw
            d.polygon([(tx - 30 * SS, y + bh), (tx + 14 * SS, y + bh), (tx, y + bh - 30 * SS)], fill=col)
        else:
            d.polygon([(x + 30 * SS, y + bh), (x - 14 * SS, y + bh), (x, y + bh - 30 * SS)], fill=col)
        tc = OUT_TEXT if side == "out" else IN_TEXT
        for k, l in enumerate(lines):
            d.text((x + pad_x, y + pad_y + k * lh), l, font=f, fill=tc)
        mc = META_OUT if side == "out" else META_IN
        mw = d.textlength(meta, font=fm)
        d.text((x + bw - pad_x - mw + 10 * SS, y + bh - pad_y - 26 * SS), meta, font=fm, fill=mc)
        y += bh + gap
    # header on top, so older messages scroll under it like in Telegram
    img.paste(head, (0, 0))
    img = img.resize((width, height), Image.LANCZOS)
    # rounded card corners
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=44, fill=255)
    img.putalpha(mask)
    return img


SCENE3 = [
    ("out", "Мисед, ты любишь подписчиков?"),
    ("in", "Да"),
    ("out", "Ты щедрый?"),
    ("in", "Да"),
    ("out", "Ты дарил подарки незнакомцам?"),
    ("in", "Да"),
    ("out", "Значит, подаришь и мне"),
    ("in", "Нет"),
]

if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "build" / "chat_preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    card = chat_card(SCENE3, times=["21:04", "21:04", "21:05", "21:05", "21:05", "21:06", "21:06", "21:06"])
    bg = Image.open(HERE / "refs" / "bg_classroom.png").convert("RGBA").resize((1080, 1920))
    bg.alpha_composite(Image.new("RGBA", bg.size, (0, 0, 0, 120)))
    bg.alpha_composite(card, ((1080 - card.width) // 2, 560))
    bg.convert("RGB").save(out)
    print(out)
