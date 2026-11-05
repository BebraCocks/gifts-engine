"""Telegram chat on a phone screen (iOS-like, own drawing), rendered as a pure function of time.
Copied from 06-petya-scam; added for 07: bear(t, side) — the plain 15 ⭐ bear gift card (own drawing),
chat_list(t, rows) — the chats list with per-row appear time, «typing» and a red BAN stamp.

    chat = dict(theme='day', name='Дима', status='в сети', avatar=img, clock='16:20', events=[...])
    screen = chat_screen(t, chat)            # RGBA SCREEN-sized image
    dev = phone(screen)                      # the same inside a phone body (DEVICE size)

Events (t = seconds on the scene clock):
    msg(t, 'out'|'in', text, clock)          text bubble; outgoing shows ✓ then ✓✓
    gift(t, 'in'|'out', name, model, backdrop, caption)   gift card with a live Lottie model
    typing(t0, t1)                           the other side is typing: «печатает…» + dots bubble
    draft(t0, t1, text)                      our side types in the input field, sends at t1
    note(t, text)                            centred service pill («Пользователь заблокирован»)
    blocked(t)                               the input bar becomes «Разблокировать»
    status(t, text)                          header status changes («в сети», «был(а) только что»)
"""
import functools
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402

FONT_DIR = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'

SCREEN = (940, 1840)
DEVICE = (980, 1880)
TOP = 236            # status bar + header
BAR = 130            # input bar height

THEMES = {
    'day': dict(wall=((214, 230, 186), (176, 206, 160)), doodle=(150, 186, 132), head=(248, 248, 250),
                head_line=(214, 214, 220), name=(10, 10, 12), status=(142, 142, 148), accent=(0, 122, 255),
                in_b=(255, 255, 255), out_b=(232, 252, 214), text=(10, 10, 12), meta_in=(150, 150, 156),
                meta_out=(84, 166, 86), bar=(248, 248, 250), field=(255, 255, 255), field_line=(216, 216, 222),
                hint=(170, 170, 176), pill=(70, 98, 60), clock=(10, 10, 12), danger=(235, 64, 52)),
    'night': dict(wall=((18, 24, 34), (10, 14, 22)), doodle=(30, 38, 52), head=(26, 30, 40),
                  head_line=(40, 44, 56), name=(244, 246, 250), status=(130, 138, 156), accent=(90, 170, 255),
                  in_b=(34, 40, 52), out_b=(44, 84, 132), text=(244, 246, 250), meta_in=(130, 138, 156),
                  meta_out=(150, 196, 250), bar=(26, 30, 40), field=(16, 20, 28), field_line=(44, 50, 64),
                  hint=(110, 118, 134), pill=(0, 0, 0), clock=(244, 246, 250), danger=(255, 90, 80)),
}


# ------------------------------------------------------------------ events
def msg(t, side, text, clock='', read=0.8):
    return dict(k='msg', t=t, side=side, text=text, clock=clock, read=read)


def gift(t, side, name, model, backdrop=None, caption='', symbol=None):
    return dict(k='gift', t=t, side=side, name=name, model=model, backdrop=backdrop, caption=caption,
                symbol=symbol)


def bear(t, side, caption=''):
    return dict(k='bear', t=t, side=side, caption=caption)


def typing(t0, t1):
    return dict(k='typing', t=t0, t1=t1)


def draft(t0, t1, text):
    return dict(k='draft', t=t0, t1=t1, text=text)


def note(t, text):
    return dict(k='note', t=t, text=text)


def blocked(t):
    return dict(k='blocked', t=t)


def status(t, text):
    return dict(k='status', t=t, text=text)


# ------------------------------------------------------------------ text with emoji
@functools.lru_cache(None)
def font(weight, size):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONT_DIR / f'SF-Pro-Text-{weight}.otf'), size)


def _is_emoji(c):
    o = ord(c)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2300 <= o <= 0x23FF or o in (0x2764, 0x2B50)


def _segments(text):
    out, cur = [], ''
    for c in text:
        if c == '️':
            continue
        if _is_emoji(c):
            if cur:
                out.append(('t', cur))
                cur = ''
            out.append(('e', c))
        else:
            cur += c
    if cur:
        out.append(('t', cur))
    return out


@functools.lru_cache(None)
def _emoji(c, size):
    from PIL import ImageFont
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new('RGBA', (136, 128), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), c, font=f, embedded_color=True)
    im = im.crop(im.getbbox() or (0, 0, 1, 1))
    s = size / max(im.size)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def text_width(text, f):
    w = 0
    for kind, s in _segments(text):
        w += f.size * 1.18 if kind == 'e' else f.getlength(s)
    return w


def draw_text(im, xy, text, f, fill):
    d = ImageDraw.Draw(im)
    x, y = xy
    for kind, s in _segments(text):
        if kind == 'e':
            e = _emoji(s, int(f.size * 1.08))
            im.alpha_composite(e, (int(x + f.size * 0.05), int(y + f.size * 0.08)))
            x += f.size * 1.18
        else:
            d.text((x, y), s, font=f, fill=fill)
            x += f.getlength(s)


def wrap(text, f, width):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split(' '):
            tryl = (cur + ' ' + w).strip()
            if text_width(tryl, f) <= width or not cur:
                cur = tryl
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ bubbles
FS = 56
LINE = 68
MAXW = 720


def _rounded(w, h, r, fill):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill)
    return im


def _checks(d, x, y, col, n):
    for k in range(n):
        ox = x + k * 11
        d.line([(ox, y + 10), (ox + 6, y + 16), (ox + 18, y + 2)], fill=col, width=3)


@functools.lru_cache(maxsize=256)
def bubble(text, side, clock, theme, read):
    T = THEMES[theme]
    f, fm = font('Regular', FS), font('Regular', 26)
    lines = wrap(text, f, MAXW)
    meta_w = fm.getlength(clock) + (40 if side == 'out' else 0)
    last_w = text_width(lines[-1], f)
    widest = max(text_width(s, f) for s in lines)
    inline = last_w + meta_w + 22 <= MAXW
    w = int(max(widest, last_w + meta_w + 22 if inline else meta_w) + 56)
    h = int(len(lines) * LINE + 34 + (0 if inline else 34))
    col = T['out_b'] if side == 'out' else T['in_b']
    im = Image.new('RGBA', (w + 14, h), (0, 0, 0, 0))
    body = _rounded(w, h, 34, col + (255,))
    bx = 0 if side == 'out' else 14
    im.alpha_composite(body, (bx, 0))
    d = ImageDraw.Draw(im)
    # tail at the bottom corner
    if side == 'out':
        d.polygon([(w - 30, h - 34), (w + 12, h), (w - 40, h)], fill=col)
    else:
        d.polygon([(44, h - 34), (2, h), (54, h)], fill=col)
    for i, s in enumerate(lines):
        draw_text(im, (bx + 28, 14 + i * LINE), s, f, T['text'])
    mc = T['meta_out'] if side == 'out' else T['meta_in']
    mx = bx + w - 20 - meta_w
    my = h - 40
    d.text((mx, my), clock, font=fm, fill=mc)
    if side == 'out':
        _checks(d, mx + fm.getlength(clock) + 8, my + 4, mc, 2 if read else 1)
    return im


@functools.lru_cache(maxsize=64)
def _gift_card_base(name, model, backdrop, caption, theme, symbol=None):
    T = THEMES[theme]
    w, h = 480, 500
    centre, edge = (90, 140, 200), (40, 70, 120)
    if backdrop:
        for b in G.backdrops(name, sorted_=False):
            if b['name'] == backdrop:
                hx = b['hex']
                centre = tuple(int(hx['centerColor'][i:i + 2], 16) for i in (1, 3, 5))
                edge = tuple(int(hx['edgeColor'][i:i + 2], 16) for i in (1, 3, 5))
                patc = tuple(int(hx['patternColor'][i:i + 2], 16) for i in (1, 3, 5))
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    # radial backdrop
    yy, xx = [v.astype('float32') for v in __import__('numpy').mgrid[0:h, 0:w]]
    import numpy as np
    r = np.clip(np.hypot(xx - w / 2, yy - 180) / 300, 0, 1)[..., None]
    rgb = np.array(centre, np.float32) * (1 - r) + np.array(edge, np.float32) * r
    bg = Image.fromarray(np.dstack([rgb, np.full((h, w, 1), 255, np.float32)]).astype(np.uint8), 'RGBA')
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 34, fill=255)
    # the backdrop pattern: the gift's symbol in two rings around the model, as on a real NFT card
    sym = symbol or G.symbols(name, sorted_=False)[0]['name']
    try:
        sp = Image.open(G.symbol_png(name, sym, 128)).convert('RGBA')
        pc = patc if backdrop else (255, 255, 255)
        tint = Image.new('RGBA', sp.size, pc + (255,))
        tint.putalpha(sp.getchannel('A').point(lambda v: int(v * 0.45)))
        lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for ring, (rr, nn, sz) in enumerate(((150, 8, 46), (215, 12, 38))):
            for j in range(nn):
                a = 2 * math.pi * (j + 0.5 * ring) / nn
                cx, cy = w / 2 + rr * math.cos(a), 180 + rr * 0.92 * math.sin(a)
                if cy > 300:
                    continue
                st = tint.resize((sz, sz), Image.LANCZOS)
                lay.alpha_composite(st, (int(cx - sz / 2), int(cy - sz / 2)))
        bg.alpha_composite(lay)
    except Exception:
        pass
    im.paste(bg, (0, 0), m)
    d = ImageDraw.Draw(im)
    ft, fs, fb = font('Bold', 38), font('Medium', 28), font('Semibold', 30)
    tw = ft.getlength(name)
    d.text(((w - tw) / 2, 318), name, font=ft, fill=(255, 255, 255))
    sub = model
    d.text(((w - fs.getlength(sub)) / 2, 366), sub, font=fs, fill=(255, 255, 255, 200))
    lab = 'Посмотреть'
    bw = fb.getlength(lab) + 64
    d.rounded_rectangle([(w - bw) / 2, 418, (w + bw) / 2, 474], 28, fill=(255, 255, 255, 60))
    d.text(((w - fb.getlength(lab)) / 2, 428), lab, font=fb, fill=(255, 255, 255))
    if caption:
        fc = font('Semibold', 28)
        cw = fc.getlength(caption) + 40
        cap = Image.new('RGBA', (w, 58), (0, 0, 0, 0))
        ImageDraw.Draw(cap).rounded_rectangle([(w - cw) / 2, 4, (w + cw) / 2, 54], 25,
                                              fill=T['pill'] + (120,))
        ImageDraw.Draw(cap).text(((w - fc.getlength(caption)) / 2, 12), caption, font=fc, fill=(255, 255, 255))
        out = Image.new('RGBA', (w, h + 66), (0, 0, 0, 0))
        out.alpha_composite(cap, (0, 0))
        out.alpha_composite(im, (0, 66))
        return out
    return im


def gift_card(e, t, theme):
    base = _gift_card_base(e['name'], e['model'], e.get('backdrop'), e.get('caption', ''), theme,
                           e.get('symbol')).copy()
    p = G.model_file(e['name'], e['model'], 'json')
    g = lottie.frame(str(p), max(0.0, t - e['t']), size=310)
    oy = 66 if e.get('caption') else 0
    base.alpha_composite(g, ((base.width - g.width) // 2, oy + 6))
    return base


@functools.lru_cache(maxsize=32)
def _note_img(text, theme):
    T = THEMES[theme]
    f = font('Semibold', 28)
    w = int(f.getlength(text) + 44)
    im = _rounded(w, 52, 26, T['pill'] + (110,))
    ImageDraw.Draw(im).text((22, 9), text, font=f, fill=(255, 255, 255))
    return im


def _dots(t, theme):
    T = THEMES[theme]
    im = Image.new('RGBA', (150, 84), (0, 0, 0, 0))
    im.alpha_composite(_rounded(136, 84, 34, T['in_b'] + (255,)), (14, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(44, 50), (2, 84), (54, 84)], fill=T['in_b'])
    for k in range(3):
        a = 0.5 + 0.5 * math.sin(t * 7 - k * 0.9)
        r = 8 + 2 * a
        c = tuple(int(v) for v in (T['meta_in'][0] * (0.6 + 0.4 * a), T['meta_in'][1] * (0.6 + 0.4 * a),
                                   T['meta_in'][2] * (0.6 + 0.4 * a)))
        cx = 50 + k * 30
        d.ellipse([cx - r, 42 - r, cx + r, 42 + r], fill=c)
    return im


# ------------------------------------------------------------------ chrome
@functools.lru_cache(maxsize=8)
def _wallpaper(theme):
    T = THEMES[theme]
    w, h = SCREEN
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    a, b = T['wall']
    for y in range(h):
        k = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)) + (255,))
    # faint doodles (hearts, stars, circles) — a nod to Telegram's pattern wallpaper
    import random
    rnd = random.Random(7)
    col = T['doodle'] + (110,)
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for gy in range(0, h + 120, 120):
        for gx in range(0, w + 120, 120):
            x, y = gx + rnd.uniform(-30, 30) + (60 if (gy // 120) % 2 else 0), gy + rnd.uniform(-30, 30)
            kind = rnd.randrange(4)
            s = rnd.uniform(14, 22)
            if kind == 0:
                dl.ellipse([x - s, y - s, x + s, y + s], outline=col, width=4)
            elif kind == 1:
                pts = [(x + s * math.cos(a_) * (1 if i % 2 == 0 else 0.45), y + s * math.sin(a_) * (1 if i % 2 == 0 else 0.45))
                       for i, a_ in enumerate([-math.pi / 2 + j * math.pi / 5 for j in range(10)])]
                dl.polygon(pts, outline=col, width=4)
            elif kind == 2:
                dl.line([(x - s, y), (x + s, y)], fill=col, width=4)
                dl.line([(x, y - s), (x, y + s)], fill=col, width=4)
            else:
                dl.arc([x - s, y - s * 0.6, x + s, y + s * 1.2], 200, 340, fill=col, width=4)
    im.alpha_composite(lay)
    return im


def _status_bar(im, T, clock):
    d = ImageDraw.Draw(im)
    f = font('Semibold', 34)
    d.text((86, 40), clock, font=f, fill=T['clock'])
    x = SCREEN[0] - 92
    d.rounded_rectangle([x, 46, x + 52, 72], 8, outline=T['clock'], width=3)
    d.rectangle([x + 5, 51, x + 38, 67], fill=T['clock'])
    d.rectangle([x + 54, 54, x + 58, 64], fill=T['clock'])
    for k in range(4):
        hh = 8 + k * 6
        d.rounded_rectangle([x - 150 + k * 12, 70 - hh, x - 142 + k * 12, 70], 2, fill=T['clock'])
    for k, r in enumerate((24, 16, 8)):
        cx, cy = x - 50, 72
        d.pieslice([cx - r, cy - r, cx + r, cy + r], 225, 315, fill=T['clock'] if k == 2 else None,
                   outline=T['clock'], width=4)


def _header(im, T, chat, st, typing_on, t):
    w = SCREEN[0]
    im.paste(im.crop((0, 0, w, TOP)).filter(ImageFilter.GaussianBlur(22)), (0, 0))   # iOS frosted header
    hd = Image.new('RGBA', (w, TOP), T['head'] + (226,))
    im.alpha_composite(hd)
    d = ImageDraw.Draw(im)
    d.line([(0, TOP - 1), (w, TOP - 1)], fill=T['head_line'], width=2)
    _status_bar(im, T, chat.get('_clock', '12:00'))
    # back
    d.line([(40, 150), (24, 168), (40, 186)], fill=T['accent'], width=5, joint='curve')
    fb = font('Regular', 34)
    d.text((54, 148), chat.get('back', 'Чаты'), font=fb, fill=T['accent'])
    # name + status
    fn, fs = font('Semibold', 36), font('Regular', 27)
    name = chat['name']
    nw = text_width(name, fn)
    draw_text(im, ((w - nw) / 2, 130), name, fn, T['name'])
    if typing_on:
        dots = '.' * (1 + int(t * 3) % 3)
        s, col = 'печатает' + dots, T['accent']
        sw = fs.getlength('печатает...')
    else:
        s, col = st, T['status']
        sw = fs.getlength(s)
    d.text(((w - sw) / 2, 178), s, font=fs, fill=col)
    av = chat.get('avatar')
    if av is not None:
        a = av.resize((84, 84), Image.LANCZOS)
        im.alpha_composite(a, (w - 120, 134))


def _draft_lines(text):
    return wrap(text, font('Regular', 34), SCREEN[0] - 290)[-4:] if text else []


def bar_height(text):
    return BAR + 44 * max(0, len(_draft_lines(text)) - 1)


def _input_bar(im, T, text, blocked_on, t, lift=0):
    w, h = SCREEN
    h = h - lift
    bh = BAR if blocked_on else bar_height(text)
    y0 = h - bh
    im.paste(im.crop((0, y0, w, h)).filter(ImageFilter.GaussianBlur(22)), (0, y0))
    bar = Image.new('RGBA', (w, bh), T['bar'] + (236,))
    im.alpha_composite(bar, (0, y0))
    d = ImageDraw.Draw(im)
    d.line([(0, y0), (w, y0)], fill=T['head_line'], width=2)
    if blocked_on:
        f = font('Regular', 36)
        s = 'Разблокировать'
        d.text(((w - f.getlength(s)) / 2, y0 + 30), s, font=f, fill=T['accent'])
        return
    yb = h - BAR          # the bottom row (icons) stays where it is, the field grows upwards
    cx, cy = 54, yb + 54
    d.line([(cx - 16, cy), (cx + 16, cy)], fill=T['hint'], width=4)
    d.line([(cx, cy - 16), (cx, cy + 16)], fill=T['hint'], width=4)
    d.rounded_rectangle([96, y0 + 22, w - 116, yb + 88], 33, fill=T['field'], outline=T['field_line'], width=2)
    f = font('Regular', 34)
    if text:
        lines = _draft_lines(text)
        for i, s in enumerate(lines):
            draw_text(im, (124, y0 + 33 + i * 44), s, f, T['text'])
        if int(t * 2.2) % 2 == 0:
            cx_ = 124 + text_width(lines[-1], f) + 3
            ly = y0 + 34 + (len(lines) - 1) * 44
            d.line([(cx_, ly), (cx_, ly + 42)], fill=T['accent'], width=3)
        d.ellipse([w - 96, yb + 24, w - 34, yb + 86], fill=T['accent'])
        d.line([(w - 65, yb + 72), (w - 65, yb + 40)], fill=(255, 255, 255), width=5)
        d.line([(w - 79, yb + 52), (w - 65, yb + 38), (w - 51, yb + 52)], fill=(255, 255, 255), width=5)
    else:
        d.text((124, yb + 33), 'Сообщение', font=f, fill=T['hint'])
        mx = w - 64
        d.rounded_rectangle([mx - 10, yb + 32, mx + 10, yb + 62], 10, outline=T['hint'], width=4)
        d.arc([mx - 18, yb + 44, mx + 18, yb + 74], 0, 180, fill=T['hint'], width=4)
        d.line([(mx, yb + 74), (mx, yb + 82)], fill=T['hint'], width=4)


KB_H = 560
KB_ROWS = ['йцукенгшщзх', 'фывапролджэ', 'ячсмитьбю']


@functools.lru_cache(maxsize=4)
def _keyboard(theme):
    T = THEMES[theme]
    w = SCREEN[0]
    dark = theme == 'night'
    bg = (32, 34, 40) if dark else (210, 213, 219)
    key = (98, 100, 108) if dark else (255, 255, 255)
    key2 = (64, 66, 74) if dark else (172, 177, 187)
    txt = (240, 240, 244) if dark else (10, 10, 12)
    im = Image.new('RGBA', (w, KB_H), bg + (255,))
    d = ImageDraw.Draw(im)
    f = font('Regular', 40)
    rects = []
    kw, kh, gap = (w - 24) / 11 - 8, 96, 8
    for r, row in enumerate(KB_ROWS):
        n = len(row)
        x0 = (w - n * (kw + gap) + gap) / 2
        y0 = 18 + r * (kh + 22)
        for i, c in enumerate(row):
            x = x0 + i * (kw + gap)
            d.rounded_rectangle([x, y0 + 3, x + kw, y0 + kh + 3], 12, fill=key2)
            d.rounded_rectangle([x, y0, x + kw, y0 + kh], 12, fill=key)
            d.text((x + kw / 2, y0 + kh / 2), c, font=f, fill=txt, anchor='mm')
            rects.append((x, y0, kw, kh))
    y3 = 18 + 3 * (kh + 22)
    d.rounded_rectangle([14, y3, 190, y3 + kh], 12, fill=key2)
    d.text((102, y3 + kh / 2), '123', font=font('Regular', 34), fill=txt, anchor='mm')
    d.rounded_rectangle([204, y3, w - 204, y3 + kh], 12, fill=key)
    d.text((w / 2, y3 + kh / 2), 'Пробел', font=font('Regular', 34), fill=txt, anchor='mm')
    d.rounded_rectangle([w - 190, y3, w - 14, y3 + kh], 12, fill=T['accent'])
    d.text((w - 102, y3 + kh / 2), 'Ввод', font=font('Regular', 34), fill=(255, 255, 255), anchor='mm')
    return im, tuple(rects)


def keyboard(theme, t, typing_on):
    base, rects = _keyboard(theme)
    if not typing_on:
        return base
    im = base.copy()
    k = int(t * 13)
    x, y, kw, kh = rects[(k * 7 + 3) % len(rects)]
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x - 6, y - 70, x + kw + 6, y + kh], 16,
                        fill=(140, 142, 150) if theme == 'night' else (240, 242, 246))
    c = ''.join(KB_ROWS)[(k * 7 + 3) % len(rects)]
    d.text((x + kw / 2, y - 22), c, font=font('Regular', 54), fill=(240, 240, 244) if theme == 'night'
           else (10, 10, 12), anchor='mm')
    return im


def kb_open(t, ev):
    """0..1 keyboard height: slides up before a draft, down 0.45 s after it is sent."""
    k = 0.0
    for e in ev:
        if e['k'] == 'draft':
            a = _ease((t - (e['t'] - 0.3)) / 0.25)
            b = 1 - _ease((t - (e['t1'] + 0.45)) / 0.3)
            k = max(k, min(a, b))
    return k


def clock_at(chat, t):
    c = chat.get('clock', '12:00')
    if isinstance(c, str):
        return c
    out = c[0][1]
    for t0, s_ in c:
        if t >= t0:
            out = s_
    return out


def _ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def chat_screen(t, chat):
    """The full screen at time t (RGBA SCREEN)."""
    theme = chat.get('theme', 'day')
    T = THEMES[theme]
    im = _wallpaper(theme).copy()
    ev = chat['events']
    st = chat.get('status', 'в сети')
    typing_on, draft_text, blocked_on = False, '', False
    items = []
    for e in ev:
        k = e['k']
        if k == 'status' and t >= e['t']:
            st = e['text']
        elif k == 'typing' and e['t'] <= t < e['t1']:
            typing_on = True
            items.append(('dots', e['t'], None))
        elif k == 'draft' and e['t'] <= t < e['t1']:
            n = len(e['text'])
            p = min(1.0, (t - e['t']) / max(0.2, (e['t1'] - e['t']) * 0.85))
            draft_text = e['text'][:int(round(n * p))]
        elif k == 'blocked' and t >= e['t']:
            blocked_on = True
        elif k in ('msg', 'gift', 'note', 'bear') and t >= e['t']:
            items.append((k, e['t'], e))
    # build sprites bottom-up
    sprites = []
    for k, t0, e in items:
        if k == 'dots':
            sprites.append(('in', _dots(t, theme), t0))
        elif k == 'msg':
            sprites.append((e['side'], bubble(e['text'], e['side'], e['clock'], theme, t >= t0 + e['read']), t0))
        elif k == 'gift':
            sprites.append(('c' if e['side'] == 'in' else 'out', gift_card(e, t, theme), t0))
        elif k == 'bear':
            sprites.append(('c', bear_card(e, t, theme), t0))
        elif k == 'note':
            sprites.append(('c', _note_img(e['text'], theme), t0))
    kb = 0.0 if blocked_on else kb_open(t, ev)
    lift = int(KB_H * kb)
    y = SCREEN[1] - lift - (BAR if blocked_on else bar_height(draft_text)) - 24
    prev = None
    for side, spr, t0 in reversed(sprites):
        g = _ease((t - t0) / 0.28)
        gap = 12 if prev in (None, side) else 26
        y -= (spr.height + gap) * g
        prev = side
        if y + spr.height < TOP - 40:
            break
        s = 0.82 + 0.18 * g
        sp = spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.BILINEAR) if g < 1 else spr
        if g < 1:
            a = sp.getchannel('A').point(lambda v, g=g: int(v * min(1.0, g * 1.6)))
            sp.putalpha(a)
        if side == 'out':
            x = SCREEN[0] - 22 - sp.width
        elif side == 'in':
            x = 22
        else:
            x = (SCREEN[0] - sp.width) // 2
        im.alpha_composite(sp, (int(x), int(y + spr.height - sp.height)))
    chat = dict(chat, _clock=clock_at(chat, t))
    _header(im, T, chat, st, typing_on, t)
    _input_bar(im, T, draft_text, blocked_on, t, lift)
    if lift > 0:
        im.alpha_composite(keyboard(theme, t, bool(draft_text)), (0, SCREEN[1] - lift))
    for fn in chat.get('overlays', ()):
        fn(im, t)
    return im


# ------------------------------------------------------------------ phone body
@functools.lru_cache(maxsize=4)
def _device(theme_dark=True):
    w, h = DEVICE
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 120, fill=(30, 32, 38))
    d.rounded_rectangle([4, 4, w - 5, h - 5], 116, outline=(84, 88, 98), width=3)
    return im


@functools.lru_cache(maxsize=2)
def _screen_mask():
    m = Image.new('L', SCREEN, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, SCREEN[0] - 1, SCREEN[1] - 1], 100, fill=255)
    return m


def phone(screen):
    dev = _device().copy()
    s = screen.copy()
    s.putalpha(Image.composite(s.getchannel('A'), Image.new('L', SCREEN, 0), _screen_mask()))
    dev.alpha_composite(s, (20, 20))
    d = ImageDraw.Draw(dev)
    cx = DEVICE[0] // 2
    d.rounded_rectangle([cx - 116, 42, cx + 116, 106], 32, fill=(0, 0, 0))      # dynamic island
    return dev


# ------------------------------------------------------------------ avatars from the characters
def head_avatar(head_img, size=240, bg=(120, 170, 230), zoom=1.0):
    """Circle avatar from a chars.head() sprite (head centre at chars.HC)."""
    import chars as C
    r = int(185 / zoom)
    cx, cy = C.HC[0], C.HC[1] + 10
    im = Image.new('RGBA', (2 * r, 2 * r), bg + (255,))
    crop = head_img.crop((cx - r, cy - r, cx + r, cy + r))
    im.alpha_composite(crop)
    im = im.resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(m)
    return im


def circle(img, size):
    im = img.resize((size, size), Image.LANCZOS).convert('RGBA')
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(Image.composite(im.getchannel('A'), Image.new('L', (size, size), 0), m))
    return im


# ------------------------------------------------------------------ 07: the plain bear gift (15 stars)
@functools.lru_cache(maxsize=8)
def _bear_card_base(caption, theme):
    import numpy as np
    T = THEMES[theme]
    w, h = 480, 470
    yy, xx = np.mgrid[0:h, 0:w].astype('float32')
    r = np.clip(np.hypot(xx - w / 2, yy - 170) / 320, 0, 1)[..., None]
    rgb = np.array((120, 170, 240), np.float32) * (1 - r) + np.array((60, 92, 180), np.float32) * r
    bg = Image.fromarray(np.dstack([rgb, np.full((h, w, 1), 255, np.float32)]).astype(np.uint8), 'RGBA')
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 34, fill=255)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    im.paste(bg, (0, 0), m)
    d = ImageDraw.Draw(im)
    ft, fs = font('Bold', 38), font('Semibold', 30)
    d.text(((w - ft.getlength('Подарок')) / 2, 318), 'Подарок', font=ft, fill=(255, 255, 255))
    lab = '⭐ 15'
    bw = text_width(lab, fs) + 64
    d.rounded_rectangle([(w - bw) / 2, 380, (w + bw) / 2, 436], 28, fill=(255, 255, 255, 60))
    draw_text(im, ((w - text_width(lab, fs)) / 2, 390), lab, fs, (255, 255, 255))
    if caption:
        fc = font('Semibold', 28)
        cw = fc.getlength(caption) + 40
        out = Image.new('RGBA', (w, h + 66), (0, 0, 0, 0))
        ImageDraw.Draw(out).rounded_rectangle([(w - cw) / 2, 4, (w + cw) / 2, 54], 25, fill=T['pill'] + (120,))
        ImageDraw.Draw(out).text(((w - fc.getlength(caption)) / 2, 12), caption, font=fc, fill=(255, 255, 255))
        out.alpha_composite(im, (0, 66))
        return out
    return im


def bear_card(e, t, theme):
    base = _bear_card_base(e.get('caption', ''), theme).copy()
    lt = max(0.0, t - e['t'])
    p = lottie.frame(str(G.original_file('5170233102089322756', 'json')), lt, size=320)   # the real 15 ⭐ bear
    oy = 66 if e.get('caption') else 0
    hop = int(-24 * abs(math.sin(min(lt, 0.9) * math.pi / 0.9)) * (1 - min(lt, 0.9)))
    base.alpha_composite(p, ((base.width - p.width) // 2, oy + hop))
    return base


def _blink(t, every=2.7):
    p = t % every
    return max(0.0, 1 - abs(p - 0.08) / 0.08) if p < 0.16 else 0.0


# ------------------------------------------------------------------ 07: chats list
def avatar_letter(letter, col, size=110):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top, bot = tuple(min(255, int(c * 1.18)) for c in col), col
    for y in range(size):
        k = y / size
        d.line([(0, y), (size, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)) + (255,))
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(m)
    f = font('Semibold', int(size * 0.44))
    if _is_emoji(letter[0]):
        e = _emoji(letter[0], int(size * 0.5))
        im.alpha_composite(e, ((size - e.width) // 2, (size - e.height) // 2))
    else:
        ImageDraw.Draw(im).text((size / 2, size / 2 + 2), letter, font=f, fill=(255, 255, 255), anchor='mm')
    return im


ROW_H = 150


@functools.lru_cache(maxsize=64)
def _row(name, last, clock, col, letter, theme, unread):
    T = THEMES[theme]
    w = SCREEN[0]
    im = Image.new('RGBA', (w, ROW_H), T['head'] + (255,))
    im.alpha_composite(avatar_letter(letter, col), (28, 20))
    fn, fl, fc = font('Semibold', 36), font('Regular', 32), font('Regular', 28)
    draw_text(im, (164, 26), name, fn, T['name'])
    draw_text(im, (164, 78), last, fl, T['status'])
    d = ImageDraw.Draw(im)
    d.text((w - 36 - fc.getlength(clock), 30), clock, font=fc, fill=T['status'])
    if unread:
        s = str(unread)
        bw = max(44, fc.getlength(s) + 26)
        d.rounded_rectangle([w - 36 - bw, 80, w - 36, 124], 22, fill=T['accent'])
        d.text((w - 36 - bw / 2, 102), s, font=fc, fill=(255, 255, 255), anchor='mm')
    d.line([(164, ROW_H - 1), (w, ROW_H - 1)], fill=T['head_line'], width=2)
    return im


@functools.lru_cache(maxsize=4)
def _stamp(text='БАН', w=330, h=120):
    lay = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    col = (230, 52, 52)
    d.rounded_rectangle([20, 20, 20 + w, 20 + h], 18, outline=col + (255,), width=10)
    f = font('Heavy', 84)
    d.text((20 + w / 2, 20 + h / 2 + 4), text, font=f, fill=col + (255,), anchor='mm')
    return lay.rotate(-12, resample=Image.BICUBIC, expand=True)


def chat_list(t, rows, theme='day', clock='12:00', title='Чаты'):
    """rows: dicts name, last, clock, col, letter, t (appear), unread, ban (stamp time or None)."""
    T = THEMES[theme]
    w, h = SCREEN
    im = Image.new('RGBA', SCREEN, T['head'] + (255,))
    d = ImageDraw.Draw(im)
    _status_bar(im, T, clock)
    d.text((36, 110), 'Изм.', font=font('Regular', 34), fill=T['accent'])
    d.text((w / 2, 128), title, font=font('Semibold', 36), fill=T['name'], anchor='mm')
    d.rounded_rectangle([28, 176, w - 28, 238], 20, fill=(236, 236, 240) if theme == 'day' else (40, 44, 56))
    d.text((70, 190), 'Поиск', font=font('Regular', 32), fill=T['hint'])
    y = 260
    for r in rows:
        g = _ease((t - r['t']) / 0.3)
        if g <= 0:
            continue
        row = _row(r['name'], r['last'], r['clock'], r['col'], r['letter'], theme, r.get('unread', 0))
        if r.get('dim', 0) > 0:
            row = row.copy()
            ov = Image.new('RGBA', row.size, (255, 230, 230, int(140 * min(1.0, r['dim']))))
            row.alpha_composite(ov)
        x = int((1 - g) * 120)
        a = row if g >= 1 else _alpha(row, g)
        im.alpha_composite(a, (x, int(y)))
        b = r.get('ban')
        if b is not None and t >= b:
            k = min(1.0, (t - b) / 0.16)
            s = 1.8 - 0.8 * fx_out(k)
            st = _stamp()
            st = st.resize((int(st.width * s * 0.62), int(st.height * s * 0.62)), Image.BILINEAR)
            im.alpha_composite(_alpha(st, min(1.0, k * 1.5)), (int(w - 230 - st.width / 2), int(y + ROW_H / 2 - st.height / 2)))
        y += ROW_H
    return im


def fx_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def _alpha(im, a):
    im = im.copy()
    im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    return im
