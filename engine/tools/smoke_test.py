"""Exercise portable primitives and the real banner in temporary storage; never builds a full video."""
import argparse
import gzip
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageDraw
import paths
import fx
import captions
import layout
import lottie
import banner


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--online-gifts', action='store_true', help='Read public gift metadata and one new animation, no account required')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='telegram-video-check-') as directory:
        paths.CACHE = Path(directory)
        check(abs(fx.smooth(0)) < 1e-8 and abs(fx.smooth(1)-1) < 1e-8, 'Easing endpoints')
        for weight in ('Regular', 'Medium', 'Semibold', 'Bold', 'Heavy'):
            font = fx.font(weight, 40)
            check(font.getlength('Подарки Telegram') > 0, 'Cyrillic font')
        ink = layout.ink('Проверка', 48)
        x, base = layout.centered('Проверка', 48, cx=540, cy=500)
        check(abs(x + (ink[0]+ink[2])/2 - 540) < 0.01, 'Text centering')
        cap = captions.Captions([captions.phrase([('Новая', 0.0), ('тема', 0.5)], end=2)], size=48)
        check(cap.layer(0.8) is not None, 'Word captions')
        canvas = np.zeros((1920, 1080, 3), np.float32)
        sprite = Image.new('RGBA', (80, 80), (255, 0, 0, 255))
        fx.over(canvas, fx.warp(sprite, 540, 960, 1))
        check(canvas[960, 540, 0] > 0.9, 'Sprite compositing')
        # Generated test vector, not a bundled media asset.
        animation = {'v': '5.7.4', 'fr': 30, 'ip': 0, 'op': 30, 'w': 100, 'h': 100,
                     'layers': [{'ddd': 0, 'ind': 1, 'ty': 1, 'nm': 'test', 'sw': 20, 'sh': 20, 'sc': '#ff0000',
                                 'ks': {'o': {'a': 0, 'k': 100}, 'r': {'a': 0, 'k': 0},
                                        'p': {'a': 1, 'k': [{'t': 0, 's': [20, 50, 0], 'e': [80, 50, 0],
                                                           'i': {'x': 0.66, 'y': 1}, 'o': {'x': 0.33, 'y': 0}},
                                                          {'t': 29, 's': [80, 50, 0]}]},
                                        'a': {'a': 0, 'k': [10, 10, 0]}, 's': {'a': 0, 'k': [100, 100, 100]}},
                                 'ao': 0, 'ip': 0, 'op': 30, 'st': 0, 'bm': 0}]}
        file = Path(directory) / 'generated-test.json'
        file.write_text(json.dumps(animation), encoding='utf-8')
        first = np.asarray(lottie.frame(file, 0, 100))
        second = np.asarray(lottie.frame(file, 0.6, 100))
        check(first[..., 3].max() > 0 and not np.array_equal(first, second), 'Live Lottie playback')
        check(np.array_equal(first, np.asarray(lottie.frame(file, 1.0, 100))), 'Full forward loop')
        compressed = Path(directory) / 'generated-test.tgs'
        compressed.write_bytes(gzip.compress(json.dumps(animation).encode('utf-8')))
        check(lottie.info(compressed)['frames'] == 30, 'TGS source cycle')
        check(np.array_equal(first, np.asarray(lottie.frame(compressed, 0, 100))), 'TGS playback')
        br = banner.Breaks([3.0])
        n, fps = banner.info()
        check(n > 1 and fps > 0, 'Banner metadata')
        rgb, alpha = banner._frame(n//2)
        check(alpha.max() > 0.5 and alpha.min() < 0.1, 'Banner alpha')
        check(rgb.shape[1] == 1080 and rgb.shape[0] / 1920 >= 0.25, 'Banner occupies >=25%')
        check(br.cy == 960, 'Banner centered')
        inside = 3.0 + banner.RAMP/2 + banner.PRE + br.B/2
        check(abs(br.content_t(inside)-3.0) < 1e-8, 'Content freezes during advertisement')
        times = np.linspace(0, br.out_dur(7), 1000)
        mapped = np.array([br.content_t(float(t)) for t in times])
        check(np.all(np.diff(mapped) >= -1e-6), 'Timeline monotonic')
        check(abs(mapped[-1]-7) < 1e-6, 'Timeline resumes')
        def frame(t):
            return np.full((1920, 1080, 3), 150, np.uint8)
        rendered = br.render(frame, inside)
        check(rendered.shape == (1920, 1080, 3), 'Ad compositing')
        check(not np.array_equal(rendered, frame(3)), 'Visible advertisement')
        rate = 8000
        silent_content = np.zeros((7*rate, 2))
        mix = br.audio(silent_content, rate)
        check(np.max(np.abs(mix)) > 0.01, 'Banner audio survives without narration')
        check(abs(len(mix)/rate-br.out_dur(7)) < 1/rate, 'Audio duration matches timeline')
        for speed in (0.9, 1.2):
            try:
                banner.Breaks([3], speed=speed)
            except ValueError:
                pass
            else:
                raise RuntimeError('Invalid advertisement speed accepted')
        if args.online_gifts:
            import gifts_api as gifts
            gifts.CACHE = Path(directory) / 'gifts'
            names = gifts.all_gifts()
            check(bool(names), 'Gift API returns data')
            models = gifts.models('Plush Pepe')
            check(isinstance(models, list) and models, 'Gift model metadata')
            file = gifts.model_file('Plush Pepe', models[0]['name'], 'json')
            check(lottie.info(file)['duration'] > 0, 'Downloaded gift animation')
            check(np.asarray(lottie.frame(file, 0.2, 100))[..., 3].max() > 0, 'Downloaded gift renders')
            print('Public gifts API: OK')
        print('Motion, fonts, captions, Lottie, banner alpha/placement/time map and narration-free audio: OK')
    print('Temporary files removed; no cache or media added to the distribution')


if __name__ == '__main__':
    main()
