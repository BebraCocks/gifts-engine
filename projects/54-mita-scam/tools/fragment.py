"""Тестовый кусок ролика: python3 tools/fragment.py <нач> <кон> <имя> — время выхода (с рекламой), 60 к/с, со звуком
из build/mix.wav → renders/54-mita-scam/<имя>.mp4"""
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import os
os.chdir(HERE)
import render as R


def job(i):
    return R.out_frame(i / R.FPS, i).tobytes()


if __name__ == '__main__':
    a, b, name = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    out = HERE.parents[1] / 'renders' / '54-mita-scam' / f'{name}.mp4'
    out.parent.mkdir(parents=True, exist_ok=True)
    i0, i1 = int(a * R.FPS), int(b * R.FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{R.W}x{R.H}', '-r', str(R.FPS), '-i', '-',
           '-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', str(HERE / 'build' / 'mix.wav'),
           '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-shortest', str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(int(os.environ.get('VIZ_WORKERS', 4))) as pool:
        for k, buf in enumerate(pool.imap(job, range(i0, i1), chunksize=4)):
            p.stdin.write(buf)
            if k % 120 == 0:
                print(f'{100 * k / (i1 - i0):.0f} %', flush=True)
    p.stdin.close()
    p.wait()
    print('готово', out)
