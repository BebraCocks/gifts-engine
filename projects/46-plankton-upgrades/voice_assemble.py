"""Собирает голос по таймлайну: дубли Fish Audio -> build/review/voice_only.mp3 и build/voice/cues.txt.
Речь 1,2x (atempo, без смены тона), RubUp 1,1x в паузе раунда 2."""
import subprocess, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')
V = os.path.join(D, 'voice')
BANNER = os.path.join(D, '..', '..', '..', 'input', 'video', 'RubUP Gifts banner.mov')
SPEED = 1.2
GAIN = {'narrator': -14.4, 'plankton1': -15.4, 'plankton2': -14.4, 'sponge': -15.6, 'squid': -19.0, 'krabs': -13.7}
# (id, файл, начало, конец, пауза после, текст)
SEQ = [
 ('N1', 'narrator', 0.00, 2.49, .25, 'Из чего улучшили Скибиди-туалет?'),
 ('P1', 'plankton1', 0.00, 2.75, .45, 'Хе-хе! Спорим, я угадаю быстрее тебя?'),
 ('N2', 'narrator', 4.11, 7.86, .20, 'Раунд один. Красный лобстер. Из какого подарка?'),
 ('P2', 'plankton1', 3.55, 7.11, 1.0, 'Морское — значит, надувной круг! Элементарно!'),
 ('N3', 'narrator', 8.55, 9.33, .15, 'Из лапши.'),
 ('P3', 'plankton1', 7.81, 9.89, .10, 'Что-о?! Лапша?!'),
 ('SB', 'sponge', 0.00, 4.39, .40, 'Ха-ха-ха! Планктон, это же лапша! Даже я знал!'),
 ('N4', 'narrator', 12.76, 16.59, .60, 'Раунд два. Павел Дуров. Из какого подарка?'),
 ('AD', None, 0, 0, .50, 'RubUp'),
 ('P4', 'plankton2', 0.00, 2.45, .35, 'Дуров? Из кепки Дурова, ха!'),
 ('N5', 'narrator', 17.31, 18.26, .15, 'Из календаря.'),
 ('P5', 'plankton2', 3.28, 4.59, .10, 'Да как так?!'),
 ('SQ', 'squid', 0.00, 4.20, .40, 'Календарь, Планктон. Даже мой кларнет умнее тебя.'),
 ('N6', 'narrator', 21.72, 25.44, .20, 'Финал. Скибиди-туалет. Из какого подарка?'),
 ('P6', 'plankton2', 5.45, 8.69, 1.0, 'Туалет — значит, какашка! Логично!'),
 ('N7', 'narrator', 26.09, 30.00, .20, 'Из горшка с монетами! Один раз из тысячи.'),
 ('KR', 'krabs', 0.00, 5.20, .15, 'Ар-ар-ар! Горшок с денежками! Уж в деньгах-то я разбираюсь!'),
 ('P7', 'plankton2', 9.48, 13.13, .35, 'Ноль — три?! Я ещё вернусь!'),
 ('N8', 'narrator', 30.45, 33.57, .30, 'А ты сколько угадал? Пиши в комментариях.'),
]
inputs, filt, labels, cues, t = [], [], [], [], 0.2
idx = {}
def inp(path):
    if path not in idx:
        idx[path] = len(inputs); inputs.append(path)
    return idx[path]
filt.append(f'anullsrc=r=48000:cl=stereo,atrim=0:0.2[lead]'); labels.append('[lead]')
for k, (cid, f, a, b, gap, txt) in enumerate(SEQ):
    if cid == 'AD':
        i = inp(BANNER); d = 6.1 / 1.1
        filt.append(f'[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,atempo=1.1,apad=pad_dur={gap}[s{k}]')
    else:
        i = inp(os.path.join(V, f + '.mp3')); d = (b - a) / SPEED
        g = -16 - GAIN[f]
        filt.append(f'[{i}:a]atrim={a}:{b},asetpts=N/SR/TB,aformat=sample_rates=48000:channel_layouts=stereo,'
                    f'atempo={SPEED},volume={g:.1f}dB,afade=t=in:d=0.02,afade=t=out:st={max(d-0.04,0):.3f}:d=0.04,apad=pad_dur={gap}[s{k}]')
    labels.append(f'[s{k}]'); cues.append(f'{t:6.2f}–{t+d:6.2f}  {cid}  {txt}'); t += d + gap
filt.append(''.join(labels) + f'concat=n={len(labels)}:v=0:a=1,alimiter=limit=0.89[o]')
cmd = ['ffmpeg', '-v', 'error', '-y']
for p in inputs: cmd += ['-i', p]
os.makedirs(os.path.join(D, 'review'), exist_ok=True)
out = os.path.join(D, 'review', 'voice_only.mp3')
cmd += ['-filter_complex', ';'.join(filt), '-map', '[o]', '-b:a', '192k', out]
subprocess.run(cmd, check=True)
open(os.path.join(V, 'cues.txt'), 'w').write('\n'.join(cues) + f'\nИтого {t:.2f} с\n')
print('\n'.join(cues)); print(f'Итого {t:.2f} с')
