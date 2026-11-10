"""Draft motion preview (not the final build): 30 fps, 540 x 960, with build/mix.wav.
python -B preview.py [out.mp4] -> build/review/preview_draft.mp4"""
import os
import subprocess
import sys
from multiprocessing import Pool
import numpy as np
from PIL import Image
import render as R

FPS = 30


def frame(i):
    return np.asarray(Image.fromarray(R.render_at(i / FPS)).resize((540, 960), Image.BILINEAR)).tobytes()


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else str(R.HERE / 'build' / 'review' / 'preview_draft.mp4')
    n = int(R.DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960', '-r', str(FPS),
           '-i', '-', '-i', str(R.HERE / 'build' / 'mix.wav'), '-map', '0:v', '-map', '1:a', '-c:v', 'libx264',
           '-crf', '23', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for k, b in enumerate(pool.imap(frame, range(n), chunksize=4)):
            p.stdin.write(b)
            if k % (n // 10) == 0:
                print(f'PROGRESS {100 * k // n}%', flush=True)
    p.stdin.close()
    p.wait()
    print('->', out)
