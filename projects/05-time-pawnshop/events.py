"""Shared content-time events (picture and sound). Word anchors come from Fish Audio ASR (words.py)."""
from timeline import DUR, ON, END, KEY
from words import wt


def line(key):
    k = KEY[key]
    return ON[k], END[k]


AD_STOP = (END[KEY['safe']] + ON[KEY['lot']]) / 2           # RubUp after the cliffhanger «главный лот…»

# scene starts (content seconds)
S = {
    'hook': 0.0,
    'room': ON[KEY['invite']] - 0.25,
    'bot': ON[KEY['bot']],
    'shop': wt('bot', 'подарки', end=True) - 0.1,
    'rule': ON[KEY['rule']] - 0.1,
    'rich': ON[KEY['rich']] - 0.15,
    'safe': ON[KEY['safe']] - 0.1,
    'lot': ON[KEY['lot']] - 0.05,
    'sign': ON[KEY['sign']] - 0.1,
    'never': ON[KEY['never']] - 0.2,
    'return': ON[KEY['return']] - 0.25,
    'refuse': ON[KEY['refuse']] - 0.1,
    'you': ON[KEY['you']] - 0.15,
    'vote': ON[KEY['vote']] - 0.15,
    'end': DUR,
}

E = {
    # hook: Pepe drops on the counter, the Saturday page burns
    'pepe_land': wt('hook', 'Пеппи') + 0.05,
    'page_burn': wt('hook', 'бабушкой'),
    # invite: grandma's cake gift arrives
    'cake_msg': wt('invite', 'Бабушка'),
    'cake_text': wt('invite', 'субботу'),
    # bot
    'bot_msg': wt('bot', 'бот'),
    'bot_text': wt('bot', 'Ламбард'),
    # cheap deals
    'tear1': wt('cheap', 'Час'),
    'cookie': wt('cheap', 'Куки'),
    'tear2': wt('cheap', 'Проспанные'),
    'globe': wt('cheap', 'Глоб'),
    # rule
    'rule_a': wt('rule', 'чем'),
    'rule_b': wt('rule', 'тем'),
    # rich
    'tear3': wt('rich', 'Лето'),
    'player': wt('rich', 'рекорд'),
    'tear4': wt('rich', 'пропущенная'),
    'cap': wt('rich', 'дура'),
    # safe
    'safe_open': wt('safe', 'достал'),
    'safe_light': wt('safe', 'главный'),
    # lot
    'pepe_reveal': ON[KEY['lot']],
    'price_tag': wt('lot', 'Цена'),
    'saturday': wt('lot', 'суббота'),
    # sign
    'shrug': wt('sign', 'другой'),
    'signs': wt('sign', 'подписал'),
    # never
    'stop_tick': ON[KEY['never']] - 0.05,
    # return
    'pour': wt('return', 'принес'),
    'please': wt('return', 'Верните'),
    # refuse
    'no': ON[KEY['refuse']],
    'profile': wt('refuse', 'Дороже'),
    'grandma_gift': wt('refuse', 'нельзя'),
    # you
    'turn': ON[KEY['you']],
    'slide': wt('you', 'плюш'),
    'waits': wt('you', 'ждет'),
    # vote
    'card_l': wt('vote', 'лягушка'),
    'card_r': wt('vote', 'часы'),
}
