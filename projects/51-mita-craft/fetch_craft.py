"""Крафтовые модели (api.changes.tg: crafted=true, rarityTier) + самый дешёвый лот каждой на Fragment → data/craft_<дата>.json"""
import json, re, sys, time, urllib.parse, urllib.request, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import gifts_api as G
UA = {'User-Agent': 'Mozilla/5.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode()
def lots(gift, model, n=1):
    slug = re.sub(r'[^a-z0-9]', '', gift.lower())
    q = {'filter': 'sale', 'sort': 'price_asc', 'attr[Model]': json.dumps([model])}
    h = get(f'https://fragment.com/gifts/{slug}?' + urllib.parse.urlencode(q))
    items = re.findall(rf'href="/gift/({slug}-\d+)[^"]*" class="tm-grid-item">.*?tm-value icon-before icon-ton">([\d,.]+)<', h, re.S)
    return [(i, float(p.replace(',', ''))) for i, p in items[:n]]
rate = json.loads(get('https://tonapi.io/v2/rates?tokens=ton&currencies=rub'))['rates']['TON']['prices']['RUB']
out = {'_note': f'Fragment «в продаже», самый дешёвый лот модели, {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC; курс tonapi.io', 'ton_rub': rate, 'gifts': {}}
for g in ('Desk Calendar', 'Jingle Bells', 'Resistance Dog', 'Myth Mask'):
    ms = [m for m in G.models(g) if m.get('crafted')]
    reg = [m for m in G.models(g) if not m.get('crafted')]
    rf = lots(g, reg[-1]['name']) if reg else []
    out['gifts'][g] = {'regular_cheap_model': reg[-1]['name'] if reg else None, 'regular_floor': rf, 'crafted': []}
    for m in ms:
        try:
            l = lots(g, m['name'])
        except Exception as e:
            l = []
        out['gifts'][g]['crafted'].append({'model': m['name'], 'tier': m.get('rarityTier'), 'floor': l})
        print(g, m['name'], m.get('rarityTier'), l, flush=True)
        time.sleep(0.3)
Path('data').mkdir(exist_ok=True)
Path(f'data/craft_{datetime.date.today()}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
