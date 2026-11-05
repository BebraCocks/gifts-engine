"""Shared content-time events (picture and sound). Word anchors come from Fish Audio ASR (words.py)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = (END[KEY['wait']] + ON[KEY['friends']]) / 2        # RubUp = the hero «просто ждёт»


def on(key, d=0.0):
    return ON[KEY[key]] + d


S = {                                   # scene starts (content seconds)
    'hook': 0.0,
    'p1': on('p1', -0.15),
    'chats': on('chats', -0.08),
    'grind': on('grind', -0.06),
    'gift': on('ban', -0.03),
    'banlist': wt('ban', 'вместе') - 0.05,
    'p2': on('p2', -0.2),
    'street': on('street', -0.2),
    'wait': on('wait', -0.06),
    'friends': on('friends', -0.07),
    'nofriends': on('nofriends', -0.12),
    'p3': on('p3', -0.25),
    'sofa': on('sofa', -0.06),
    'dm': on('dm', -0.06),
    'auto': on('auto', -0.1),
    'like': on('like', -0.3),
    'end': DUR,
}

E = {
    'bear_land': wt('hook', 'мишку') + 0.1,
    'price': wt('hook', '15'),
    'cards': wt('hook', 'Три'),
    'best': wt('hook', 'конце'),
    'flip1': wt('p1', 'место'),
    'stamp1': wt('p1', 'о'),                       # «ПРОСЬБА О БЛАГОСКЛОННОСТИ» lands on «о»
    'rich': wt('chats', 'богатых'),
    'hours': wt('grind', '10'),
    'luck': wt('grind', 'удача'),
    'gift_in': wt('ban', 'получите'),
    'ban': wt('ban', 'баном'),
    'flip2': wt('p2', 'место'),
    'effect': wt('p2', 'эффективный'),
    'change': wt('street', 'старой'),
    'sign_up': wt('street', 'картинкой'),
    'crowd': wt('wait', 'людное'),
    'coin': wt('wait', 'ждете'),
    'friend_in': wt('friends', 'проходили'),
    'spotted': wt('friends', 'друзья'),
    'dust': wt('nofriends', 'есть'),
    'flip3': wt('p3', 'место'),
    'meter': wt('p3', 'работает'),
    'full': wt('p3', '100'),
    'couch': wt('sofa', 'дивана'),
    'type0': wt('dm', 'фразу'),
    'send': wt('dm', 'У', end=True),                # «дай ми-ше-у» read by syllables (v2)
    'autow': wt('auto', 'автоматически'),
    'ask': wt('auto', 'просите'),
    'like_btn': wt('like', 'лайк'),
    'bear_wave': wt('like', 'мишку'),
}
