"""Start with a neutral preview; define the new visual style before a full build."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw
import banner
import frames
import fx
import gifts_api
import lottie
import config
from script import LINES
from timeline import DUR, ON, END
from events import AD_STOP

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([AD_STOP], cy=H/2)
ANIMATION = None
if config.GIFT_NAME and config.MODEL_NAME:
    ANIMATION = gifts_api.model_file(config.GIFT_NAME, config.MODEL_NAME, 'json')


def render_at(t):
    im = Image.new('RGB', (W, H), config.BACKGROUND)
    draw = ImageDraw.Draw(im)
    index = max((k for k, start in enumerate(ON) if t >= start), default=0)
    font = fx.font(config.FONT_WEIGHT, config.FONT_SIZE)
    # A placeholder for composition, not a recommended look for future videos.
    text = LINES[index][1]
    draw.multiline_text((W/2, 520), text, font=font, fill=config.TEXT_COLOR, anchor='mm', align='center')
    if ANIMATION:
        gift = lottie.frame(str(ANIMATION), t, size=600)
        im.paste(gift, (240, 750), gift)
    return np.asarray(im).copy()


def frame_bytes(i):
    return BR.render(render_at, i/FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
