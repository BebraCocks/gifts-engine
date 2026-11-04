"""Shared content-time events: shot cuts, RubUp stops and word anchors (picture and sound use the same)."""
from timeline import DUR, ON, END
from words import wt

RAMP = 0.4                     # banner.RAMP


def _stop(k):
    """Stop the video right after line k (0-based) ends, before the next line starts."""
    return max(END[k], min(END[k] + 0.1 + RAMP / 2, ON[k + 1] - RAMP / 2 - 0.02))


AD_STOPS = [_stop(4), _stop(12)]          # after the gift tease (~30 s) and after "there are rarer models" (~92 s out)


def _mid(k):
    return (END[k - 1] + ON[k]) / 2


SOLD_SPLIT = wt(9, 'многие') - 0.12
CUTS = [0.0, _mid(1), _mid(2), _mid(3), _mid(4), AD_STOPS[0], _mid(6), _mid(7), _mid(8), SOLD_SPLIT, _mid(9),
        _mid(10), _mid(11), AD_STOPS[1], _mid(14), _mid(15), DUR]
NAMES = ['S01_desk', 'S02_office', 'S05_court', 'S06_roof', 'S04_vault', 'S07_ipcity', 'S09_legend', 'S15_phone',
         'S11_giftrain', 'S10_ton', 'S16_hacker', 'S17_havana', 'S18_arena', 'S19_crypto', 'S13_laser', 'S14_final']
SHOTS = [(n, CUTS[i], CUTS[i + 1]) for i, n in enumerate(NAMES)]


def shot_at(t):
    for n, a, b in SHOTS:
        if t < b or n == NAMES[-1]:
            return n, a, b


E = dict(
    war=wt(1, 'стал'), spotty=wt(2, 'Спотти'), said=wt(2, 'говорят'), durov1=wt(2, 'Дуров'),
    april=wt(3, 'В'), y2018=wt(3, 'восемнадцатом'), keys=wt(3, 'ключи'), court=wt(3, 'шифрования'),
    blocks=wt(3, 'заблокировали'),
    pub=wt(4, 'А Дуров'), hood=wt(4, 'капюшон'), sign=wt(4, 'Цифровое'), resist=wt(4, 'сопротивление'),
    today=wt(5, 'Сегодня'), gift1=wt(5, 'подарок'), models5=wt(5, 'моделей'), story=wt(5, 'история'),
    vpn=wt(6, 'VPN'), hello=wt(6, 'привет'), fall=wt(6, 'блокировке'), tg=wt(6, 'Телега'), proxy=wt(6, 'прокси'),
    lift=wt(7, 'сняли'), legend=wt(7, 'легендой'), token=wt(7, 'токен'),
    aug=wt(8, 'Четырнадцатого'), wrote=wt(8, 'написал'), hour=wt(8, 'час'), among=wt(8, 'Среди'), hooddog=wt(8, 'капюшоне'),
    sold=wt(9, 'раскупили'), seconds=wt(9, 'секунды'), many=wt(9, 'многие'), first=wt(9, 'впервые'), gifts9=wt(9, 'подарки'),
    anon=wt(10, 'Anonymous'), hacker=wt(10, 'хакер'), mask=wt(10, 'маске'), days=wt(10, 'дней'),
    che=wt(11, 'Че'), flag=wt(11, 'флагом'), cigar=wt(11, 'сигарой'), rev=wt(11, 'революционер'),
    sparta=wt(12, 'Спартак'), glad=wt(12, 'гладиатор'), leader=wt(12, 'вождь'), rebellion=wt(12, 'восстания'),
    rarer=wt(13, 'реже'),
    satoshi=wt(14, 'Сатоши'), craft=wt(14, 'крафтовая'), goldw=wt(14, 'золотом'), btc=wt(14, 'биткоином'),
    rare=wt(15, 'редкая'), imposter=wt(15, 'Imposter'), thousand=wt(15, 'тысячу'),
    drawing=wt(16, 'Рисунок'), survived=wt(16, 'пережил'), legend2=wt(16, 'легендой'), resist2=wt(16, 'Сопротивление'),
    cont=wt(16, 'продолжается'),
)
E = {k: float(v) for k, v in E.items()}

if __name__ == '__main__':
    print('ads', [round(a, 2) for a in AD_STOPS], 'out ~', round(AD_STOPS[0], 1), round(AD_STOPS[1] + 6.115, 1))
    for n, a, b in SHOTS:
        print(f'{n:13s} {a:7.2f} {b:7.2f} {b-a:5.2f}')
