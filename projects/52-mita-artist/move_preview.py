"""Превью любого движения: python3 move_preview.py имя_выхода поза1:длит поза2:длит ... → build/<имя>.mp4 (выравнивание голова+ноги)."""
import sys, subprocess
import numpy as np
from PIL import Image
import anim
import snap_preview as SP

name = sys.argv[1]
seq = [(a.split(':')[0], float(a.split(':')[1])) for a in sys.argv[2:]]
SP.align_all([n for n, _ in seq])
anim.FR = SP.AL
anim.pose.cache_clear()
T, t = [], 0.0
for n, d in seq:
    t += d
    T.append(t)
W, H, FPS = 540, 960, 60
out = SP.HERE / 'build' / f'{name}.mp4'
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)], stdin=subprocess.PIPE)
for i in range(int((t + 0.4) * FPS)):
    tt = i / FPS
    a = anim.pose(seq[-1][0])
    for k in range(1, len(seq)):
        if tt < T[k]:
            d = seq[k][1]
            u = (tt - (T[k] - d)) / d if d else 1
            a = anim.morph(seq[k - 1][0], seq[k][0], max(0.0, u)) if u > 0 else anim.pose(seq[k - 1][0])
            break
    bg = Image.new('RGBA', (W, H), (250, 248, 255, 255))
    m = Image.fromarray(a)
    m = m.resize((int(m.width * 0.72), int(m.height * 0.72)), Image.LANCZOS)
    bg.alpha_composite(m, (W // 2 - m.width // 2, 830 - int(990 * 0.72)))
    p.stdin.write(np.array(bg.convert('RGB')).tobytes())
p.stdin.close(); p.wait()
print(out, round(t, 2))
