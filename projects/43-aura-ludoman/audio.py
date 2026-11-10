"""43-aura-ludoman sound: the author's track «AURA – Ultra Slowed» whole (= video length), the voice on its cues
(music ducked under speech), SFX from input/sfx/ through sfxkit. No RubUp banner (author, 2026-11-10).
Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import wave
import numpy as np
import sfxkit
import voice_review
import events as E
from timeline import DUR, DROP1, DROP2, BREAK

SR = 48000


def ticks(kit, fx, t0, t1, key, file, gain, first=0.045, last=0.32, label=''):
    """A decelerating roulette / wheel tick train from one pack sound (a deliberate motif: key=)."""
    t, k = t0, 0
    while t < t1:
        u = (t - t0) / (t1 - t0)
        kit.add(fx, 'list', t, gain_db=gain - 4 * u, key=key, file=file, pan=0.15 * ((-1) ** k),
                label=label if k == 0 else None)
        t += first + (last - first) * u ** 2.2
        k += 1


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    a = kit.add
    # spins: roulette ticks for the cases, wheel ticks for the upgrades
    for (tp, _), stop in zip(E.PRESSES[:3], E.POPS[:3]):
        ticks(kit, fx, tp + 0.06, stop[0] - 0.12, 'roulette', 'mini-list-one-shot-2', -15, label='case roulette spins')
    for t0, t1 in ((0.0, E.HOOK_HIDE - 0.15), (E.PRESSES[3][0] + 0.06, E.LOSE - 0.1), (E.PRESSES[4][0] + 0.06, DROP2 - 0.1)):
        ticks(kit, fx, t0, t1, 'wheel', 'mini-list-one-shot.flac', -13, first=0.06, last=0.42, label='upgrade wheel spins')
    # hook: tension to «ДА!», hidden result
    a(fx, 'riser', E.HOOK_HIDE, align='end', gain_db=-21, label='hook: the final spin builds')
    a(fx, 'impact', E.HOOK_HIDE, align='peak', gain_db=-15, label='hook: «ДА!» flash')
    a(fx, 'sparkle', E.HOOK_HIDE + 0.05, gain_db=-20, label='hook: joy sparkle')
    a(fx, 'spinback', E.HOOK_END - 0.3, gain_db=-17, fit=0.45, fade_out=0.12, label='rewind to the start of the story')
    # hand presses: approach + a firm click on the button
    for k, (tp, _) in enumerate(E.PRESSES):
        a(fx, 'whoosh-short', tp, align='peak', gain_db=-24, pan=0.25, label=f'hand {k + 1}: reach')
        a(fx, 'click', tp, align='peak', gain_db=-11, pan=0.1, label=f'hand {k + 1}: press')
    # gifts pop out of the popup
    for tp, gift, *_ in E.POPS[:3]:
        a(fx, 'pop', tp, gain_db=-14, label=f'{gift} pops out')
        a(fx, 'granular-move', tp + 0.05, gain_db=-23, label=f'{gift} shimmer')
    a(fx, 'cartoon-hit', 21.45, align='peak', gain_db=-19, label='566?! the head jolts with rage')
    # every case is «неокуп»: a short fail + the red minus tag
    for ta, text, _ in E.LOSS_TAGS:
        a(fx, 'error', ta - 0.05, gain_db=-19, label=f'неокуп {text}')
        a(fx, 'glitch-text', ta, gain_db=-25, label='red minus tag')
    # upgrade 50/50 -> loss
    a(fx, 'riser', E.LOSE, align='end', gain_db=-23, label='upgrade spin builds')
    a(fx, 'error', E.LOSE, align='peak', gain_db=-13, label='«Не повезло»')
    a(fx, 'power-down', E.LOSE + 0.1, gain_db=-20, label='the fire collapses')
    a(fx, 'downlifter', 35.9, gain_db=-26, fit=1.6, label='sad: «опять мимо»')
    # break: the final upgrade
    # second drop: win
    a(fx, 'riser-hit', DROP2, align='peak', gain_db=-16, label='final spin 19.9 % builds (break) -> «Улучшено» on the drop')
    a(fx, 'confirm', DROP2 + 0.05, gain_db=-15, label='win confirm')
    a(fx, 'pop', E.POPS[3][0], gain_db=-13, label='Neko Helmet pops out')
    a(fx, 'sparkle-whoosh', E.POPS[3][0] + 0.05, gain_db=-19, label='gold rays')
    a(fx, 'sparkle', E.CONFETTI, gain_db=-18, label='win confetti')
    a(fx, 'coin', 46.0, gain_db=-20, label='6 683 stars')
    # summary «чек»: slide in, three counters, the stamp on a hit
    a(fx, 'whoosh-short', E.SUMMARY_T0 + 0.2, align='peak', gain_db=-19, label='summary slides in')
    for k, tr in enumerate(E.SUMMARY_ROWS):
        a(fx, 'counter', tr, gain_db=-21, fit=0.7, fade_out=0.15, label=('spent', 'received', 'in plus')[k] + ' counter')
    a(fx, 'impact', E.SUMMARY_STAMP, align='peak', gain_db=-15, label='«ОКУП ×2» stamp')
    a(fx, 'coin', E.SUMMARY_STAMP + 0.1, gain_db=-20, label='stamp coins')
    a(fx, 'whoosh-short', E.SUMMARY_T1 - 0.15, align='peak', gain_db=-22, label='summary flies away')
    for ta, text, _ in E.AURA_TEXT:
        a(fx, 'glitch-text', ta, gain_db=-21, label=text)
    # the helmet flies back into the win window (on the hit), bears fly
    back = E.POPS[3][0] + 0.35 + E.POPS[3][4] + 0.35
    a(fx, 'whoosh-short', back, align='peak', gain_db=-19, label='helmet flies back into the window')
    a(fx, 'pop', back, gain_db=-16, label='helmet lands in the window (bass hit)')
    for tt, hand, bears in E.THROWS:
        a(fx, 'cartoon-move', tt, gain_db=-20, pan=0.4 if hand == 'R' else -0.4, label=f'bears thrown ({hand})')
        a(fx, 'boing', tt + 0.05, gain_db=-24, pan=0.4 if hand == 'R' else -0.4, label='bear boing')
    return fx


def main():
    kit = sfxkit.Kit(HERE)
    music = voice_review.read(voice_review.TRACK, ch=2)
    n = int(round(DUR * SR))
    music = np.pad(music, ((0, max(0, n - len(music))), (0, 0)))[:n]
    v = voice_review.voice_track(n)
    v *= 0.89 / max(1e-9, np.abs(v).max())
    env = np.convolve(np.abs(v), np.ones(SR // 20) / (SR // 20), 'same')
    duck = 1 - 0.45 * np.clip(env / 0.03, 0, 1)                    # music −5 dB under speech
    duck = np.convolve(duck, np.ones(SR // 8) / (SR // 8), 'same')
    fx = sfx_layer(n, kit)
    fx *= (1 - 0.4 * np.clip(env / 0.03, 0, 1))[:, None]            # SFX step back under speech too
    mix = music * 0.58 * duck[:, None] + v[:, None] * 0.92 + fx
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    out = paths.build(HERE) / 'mix.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save()
    rev = sfxkit.write_review(HERE, fx, mix, None, SR, kit.cues)
    print('build/mix.wav; review:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')


if __name__ == '__main__':
    main()
