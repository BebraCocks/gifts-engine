"""Shared content-time events (picture and sound). Word anchors come from words.py."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['like']] + 0.2          # RubUp right after «…пока идёт реклама»; next line starts 0.35 s after it


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'land': on('hook', 0.12),
    'real': wt('real', 'настоящий'),
    'model': wt('real', 'модель'),
    'profile': wt('real', 'поставить'),
    'sold': on('sold', -0.15),
    'million': wt('sold', 'миллион'),
    'bought': wt('sold', 'раскупили'),
    'half': wt('sold', 'полчаса'),
    'want': on('want', -0.2),
    'three': wt('want', 'три'),
    'like': wt('like', 'лайк'),
    'press': wt('like', 'жми'),
    'done': wt('repost', 'поставил'),
    'nice': wt('repost', 'красавчик'),
    'repost': wt('repost', 'репост'),
    'friend': wt('repost', 'другу'),
    'comment': wt('comment', 'комментарий'),
    'what': wt('comment', 'что'),
    'bears_in': on('bears', -0.15),
    'ten': wt('bears', 'десять'),
    'bear': wt('bears', 'мишке'),
    'week': on('result', -0.1),
    'random': wt('result', 'случайно'),
    'pin': wt('result', 'закреплю'),
    'f_like': wt('final', 'лайк'),
    'f_repost': wt('final', 'репост'),
    'f_comment': wt('final', 'комментарий'),
    'f_snoop': wt('final', 'снуп'),
    'end': DUR,
}
