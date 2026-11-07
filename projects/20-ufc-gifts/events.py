"""Shared content-time events (picture and sound). L04 words from Fish ASR, the rest from the voice envelope."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['conor']] + 0.25        # RubUp after the Khabib / McGregor block (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'four_h': wt('hook', 'четыре'),
    'link': on('link', -0.2), 'copy': wt('link', 'скопируй'), 'goal': wt('link', 'просмотры'),
    'khabib': on('khabib', -0.15), 'k29': wt('khabib', 'двадцать'), 'k_day': wt('khabib', 'сутки'),
    'k_usd': wt('khabib', 'четыре'),
    'conor': on('conor', -0.1), 'scam': wt('conor', 'обманом'), 'remind': wt('conor', 'напомнили'),
    'c_jones': wt('conor', 'джонс'), 'c_ades': wt('conor', 'адесанья'), 'c_oliv': wt('conor', 'оливейра'),
    'c_ads': wt('conor', 'рекламировали'),
    'strike': on('strike', -0.15), 'name_strike': wt('strike', 'страйк'),
    's0': wt('strike', 'джонс'), 's1': wt('strike', 'перейра'), 's2': wt('strike', 'чимаев'),
    's3': wt('strike', 'топурия'), 's4': wt('strike', 'волкановски'), 's5': wt('strike', 'пятеро'),
    'sold': on('sold', -0.15), 'n60': wt('sold', 'шестьдесят'), 'auction': wt('sold', 'аукциона'),
    'hours': wt('sold', 'четыре'),
    'neon': on('neon', -0.15), 'streamer': wt('neon', 'стример'), 'n323': wt('neon', 'триста'),
    'octagon': on('octagon', -0.15), 'entry': wt('octagon', 'входа'), 'fighters_out': wt('octagon', 'бойцы'),
    'gold': on('gold', -0.15), 'golden': wt('gold', 'золотые'), 'half': wt('gold', 'половине'),
    'outro': on('outro', -0.2), 'o_profile': wt('outro', 'профиль'), 'o_write': wt('outro', 'пиши'),
    'end': DUR,
}
