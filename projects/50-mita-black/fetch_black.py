"""Fragment: самый дешёвый лот коллекции в продаже — всего и на фоне Black; редкость Black из api.changes.tg.
→ data/black_<дата>.json"""
import json, re, sys, time, urllib.parse, urllib.request, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import gifts_api as G
UA = {'User-Agent': 'Mozilla/5.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode()
def lots(gift, backdrop=None, n=3):
    slug = re.sub(r'[^a-z0-9]', '', gift.lower())
    q = {'filter': 'sale', 'sort': 'price_asc'}
    if backdrop: q['attr[Backdrop]'] = json.dumps([backdrop])
    h = get(f'https://fragment.com/gifts/{slug}?' + urllib.parse.urlencode(q))
    items = re.findall(rf'href="/gift/({slug}-\d+)[^"]*" class="tm-grid-item">.*?tm-value icon-before icon-ton">([\d,.]+)<', h, re.S)
    return [(i, float(p.replace(',', ''))) for i, p in items[:n]]
if __name__ == '__main__':
    rate = json.loads(get('https://tonapi.io/v2/rates?tokens=ton&currencies=rub,usd'))['rates']['TON']['prices']
    now = datetime.datetime.now(datetime.timezone.utc)
    out = {'_note': f'Fragment «в продаже», сортировка по цене, {now:%Y-%m-%d %H:%M} UTC; редкость фонов — api.changes.tg; курс tonapi.io',
           'ton_rub': rate['RUB'], 'gifts': {}}
    for g in G.all_gifts():
        try:
            bd = {b['name']: b['rarityPermille'] for b in G.backdrops(g)}
            if 'Black' not in bd: continue
            allf = lots(g); time.sleep(0.35); blk = lots(g, 'Black'); time.sleep(0.35)
            out['gifts'][g] = {'black_permille': bd['Black'], 'min_permille': min(bd.values()), 'max_permille': max(bd.values()),
                               'floor': allf[:1], 'black_floor': blk[:1]}
            if allf and blk: print(g, allf[0][1], blk[0][1], round(blk[0][1] / allf[0][1], 1), bd['Black'])
        except Exception as e:
            print('ERR', g, e)
    p = Path(__file__).parent / 'data' / f'black_{now:%Y-%m-%d}.json'
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1)); print(p, rate['RUB'])
