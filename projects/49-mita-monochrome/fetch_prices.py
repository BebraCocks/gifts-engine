"""Цены Fragment (лоты «в продаже», сортировка по цене) + курс TON→RUB (tonapi.io) → data/prices_<дата>.json."""
import json, re, sys, time, urllib.parse, urllib.request, datetime
from pathlib import Path
UA = {'User-Agent': 'Mozilla/5.0'}
ITEMS = [  # (подарок, модель, фон или None)
    ('Ginger Cookie', 'Sweetheart', None), ('Ginger Cookie', 'Sweetheart', 'Fandango'),
    ('Jingle Bells', 'Barbie', None), ('Jingle Bells', 'Barbie', 'Fandango'),
    ('Jester Hat', 'Pinky Circus', None), ('Jester Hat', 'Pinky Circus', 'Raspberry'),
    ('Precious Peach', 'Malachite', None), ('Precious Peach', 'Malachite', 'Malachite'),
    ('Eternal Rose', 'Moonstone', None), ('Eternal Rose', 'Moonstone', 'Moonstone'),
    ('Spiced Wine', 'Persimmon', None), ('Spiced Wine', 'Persimmon', 'Persimmon'),
    ('Plush Pepe', 'Marble', None), ('Plush Pepe', 'Marble', 'Black'),
    ('Perfume Bottle', 'Mono Delight', None), ('Perfume Bottle', 'Mono Delight', 'Black'),
    ('Santa Hat', 'Inky White', None), ('Santa Hat', 'Inky White', 'Black'),
]


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode()


def lots(gift, model, backdrop):
    slug = re.sub(r"[^a-z0-9]", '', gift.lower())
    q = {'filter': 'sale', 'sort': 'price_asc', 'attr[Model]': json.dumps([model])}
    if backdrop:
        q['attr[Backdrop]'] = json.dumps([backdrop])
    url = f'https://fragment.com/gifts/{slug}?' + urllib.parse.urlencode(q)
    h = get(url)
    ids = re.findall(rf'href="/gift/({slug}-\d+)\?', h)
    prices = [float(p.replace(',', '')) for p in re.findall(r'tm-grid-item-value tm-value icon-before icon-ton">([\d,.]+)<', h)]
    return url, list(zip(ids, prices))[:10]


if __name__ == '__main__':
    rate = json.loads(get('https://tonapi.io/v2/rates?tokens=ton&currencies=rub,usd'))['rates']['TON']['prices']
    now = datetime.datetime.now(datetime.timezone.utc)
    out = {'_note': f'Fragment, фильтр «в продаже», сортировка по цене; {now:%Y-%m-%d %H:%M} UTC. Курс tonapi.io.',
           'ton_rub': rate['RUB'], 'ton_usd': rate['USD'], 'items': []}
    for g, m, b in ITEMS:
        url, l = lots(g, m, b)
        out['items'].append({'gift': g, 'model': m, 'backdrop': b, 'url': url, 'lots': l})
        print(g, m, b, l[:3])
        time.sleep(0.7)
    p = Path(__file__).parent / 'data' / f'prices_{now:%Y-%m-%d}.json'
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(p, rate)
