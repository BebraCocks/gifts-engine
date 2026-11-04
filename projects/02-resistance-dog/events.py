"""Shared content-time events: shot cuts, RubUp stops and word anchors (picture and sound use the same)."""
from timeline import DUR, ON, END
from words import wt

RAMP = 0.4                     # banner.RAMP


def _stop(k):
    """Stop the video right after line k (0-based) ends, before the next line starts."""
    return max(END[k], min(END[k] + 0.1 + RAMP / 2, ON[k + 1] - RAMP / 2 - 0.02))


AD_STOPS = [_stop(3), _stop(10)]          # after the VPN tease (~28 s) and after the gift drop (~89 s output)


def _mid(k):
    return (END[k - 1] + ON[k]) / 2


# shot boundaries in content time: (name, start, end)
CUTS = [0.0, _mid(1), ON[2] - 0.15, _mid(3), AD_STOPS[0], _mid(5), _mid(6), _mid(7), _mid(8), _mid(9),
        _mid(10), AD_STOPS[1], _mid(12), _mid(13), DUR]
NAMES = ['S01_desk', 'S02_office', 'S03_past', 'S04_vault', 'S05_court', 'S06_roof', 'S07_ipcity',
         'S08_planes', 'S09_legend', 'S10_ton', 'S11_giftrain', 'S12_gallery', 'S13_laser', 'S14_final']
SHOTS = [(n, CUTS[i], CUTS[i + 1]) for i, n in enumerate(NAMES)]


def shot_at(t):
    for n, a, b in SHOTS:
        if t < b or n == NAMES[-1]:
            return n, a, b


# key word moments (content seconds)
E = dict(
    war=wt(1, 'стал'), spotty=wt(2, 'Спотти'), said=wt(2, 'Говорят'), durov1=wt(2, 'Дуров'),
    left=wt(3, 'ушёл'), telegram1=wt(3, 'Телеграм'), past=wt(3, 'прошлом'),
    today=wt(4, 'сегодня'), gift1=wt(4, 'подарок'), vpn=wt(4, 'VPN'), coinc=wt(4, 'Совпадение'), notat=wt(4, 'Вовсе'),
    april=wt(5, 'Апрель'), y2018=wt(5, '2018'), keys=wt(5, 'ключи'), court=wt(5, 'суд'), blocks=wt(5, 'блокирует'),
    pub=wt(6, 'публикует'), hood=wt(6, 'капюшоне'), sign=wt(6, 'Подпись'), resist=wt(6, 'сопротивление'),
    rkn=wt(7, 'Роскомнадзор'), millions=wt(7, 'миллионы'), fall=wt(7, 'падают'), tg=wt(7, 'телега'), proxy=wt(7, 'прокси'),
    planes=wt(8, 'самолётики'), models8=wt(8, 'моделей'), proxyserver=wt(8, 'Proxy'), anon=wt(8, 'Anonymous'),
    lift=wt(9, 'снимают'), legend=wt(9, 'легендой'),
    token=wt(10, 'токен'), arrest=wt(10, 'задержания'), france=wt(10, 'Франции'), avatars=wt(10, 'аватарки'),
    gifts24=wt(11, 'подарки'), year=wt(11, 'год'), him=wt(11, 'он'), next=wt(11, 'интересное'),
    upgrade=wt(12, 'улучшать'), dozens=wt(12, 'десятки'), che=wt(12, 'Че'), sparta=wt(12, 'Спартак'),
    rambo=wt(12, 'Рэмбо'), satoshi=wt(12, 'Сатоши'),
    rare=wt(13, 'редкая'), imposter=wt(13, 'Imposter'), thousand=wt(13, 'тысячу'),
    drawing=wt(14, 'Рисунок'), survived=wt(14, 'пережил'), collect=wt(14, 'коллекционным'),
    resist2=wt(14, 'Сопротивление'), cont=wt(14, 'продолжается'),
)

if __name__ == '__main__':
    print('ads', [round(a, 2) for a in AD_STOPS])
    for n, a, b in SHOTS:
        print(f'{n:13s} {a:7.2f} {b:7.2f} {b-a:5.2f}')
    print({k: round(v, 2) for k, v in E.items()})
