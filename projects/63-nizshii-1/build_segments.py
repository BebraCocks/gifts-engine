"""Сборка части 1 v2 кусками по минуте — переживает перезапуск контейнера: готовые сегменты build/seg/*.mp4
пропускаются, рендер продолжается с первого недостающего. Потом склейка без перекодирования, звук build/mix.wav
(audio.py), проверка как в engine/tools/build.py.
    python -B projects/63-nizshii-1/build_segments.py --approved --name nizshii_part1_v2"""
import json
import os
import subprocess
import sys
import time
from fractions import Fraction
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import frames  # noqa: E402
import render as r  # noqa: E402

SEG = 60.0


def main():
    if '--approved' not in sys.argv:
        raise SystemExit('Только после «собирай» автора: --approved')
    name = sys.argv[sys.argv.index('--name') + 1]
    out = HERE.parents[1] / 'renders' / HERE.name / f'{name}.mp4'
    if out.exists():
        raise SystemExit('Итоговый файл уже есть; нужен новый --name')
    build = paths.build(HERE)
    seg_dir = build / 'seg'
    seg_dir.mkdir(exist_ok=True)
    n_total = r.BR.n_frames(r.FPS, r.DUR)
    per = int(SEG * r.FPS)
    segs = [(a, min(n_total, a + per)) for a in range(0, n_total, per)]
    mix = build / 'mix.wav'
    if not mix.is_file():
        subprocess.run([sys.executable, '-B', 'audio.py'], cwd=HERE, check=True)
    enc, enc_name = frames.encoder_args(14)
    for k_ in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ.setdefault(k_, '1')
    workers = frames.cpu_workers()
    done_before = sum(b - a for k, (a, b) in enumerate(segs) if (seg_dir / f'seg_{k:02d}.mp4').is_file())
    print(f'{n_total} кадров, {len(segs)} сегментов, готово {done_before}; {workers} рабочих, {enc_name}', flush=True)
    t0 = time.time()
    done = done_before
    last_pct = int(done * 10 / n_total) * 10
    with Pool(workers, initializer=frames.low_priority) as pool:
        for k, (a, b) in enumerate(segs):
            dst = seg_dir / f'seg_{k:02d}.mp4'
            if dst.is_file():
                continue
            tmp = seg_dir / f'seg_{k:02d}.tmp.mp4'
            cmd = [paths.ffmpeg(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s',
                   f'{r.W}x{r.H}', '-r', str(r.FPS), '-i', '-'] + enc + [str(tmp)]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for bts in pool.imap(r.frame_bytes, range(a, b), chunksize=1):
                proc.stdin.write(bts)
                done += 1
                pct = int(done * 10 / n_total) * 10
                if pct > last_pct:
                    last_pct = pct
                    el = time.time() - t0
                    left = el / max(1, done - done_before) * (n_total - done)
                    print(f'PROGRESS {pct}% · кадры {done}/{n_total} · прошло {int(el // 60)} мин · '
                          f'осталось ~{int(left // 60)} мин', flush=True)
            proc.stdin.close()
            if proc.wait():
                raise SystemExit(f'ffmpeg: ошибка в сегменте {k}')
            os.replace(tmp, dst)
            print(f'сегмент {k + 1}/{len(segs)} готов', flush=True)
    print('PROGRESS · склейка сегментов и звука, проверка декодированием', flush=True)
    lst = seg_dir / 'list.txt'
    lst.write_text(''.join(f"file '{seg_dir / f'seg_{k:02d}.mp4'}'\n" for k in range(len(segs))))
    video = build / 'video_only.mp4'
    subprocess.run([paths.ffmpeg(), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy',
                    str(video)], check=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([paths.ffmpeg(), '-n', '-v', 'error', '-i', str(video), '-i', str(mix), '-map', '0:v:0', '-map',
                    '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-map_metadata', '-1',
                    '-movflags', '+faststart', str(out)], check=True)
    info = json.loads(subprocess.run([paths.ffprobe(), '-v', 'error', '-show_streams', '-of', 'json', str(out)],
                                     capture_output=True, text=True, check=True).stdout)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    au = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    if (v['width'], v['height'], v['pix_fmt'], v['codec_name']) != (1080, 1920, 'yuv420p', 'h264'):
        raise SystemExit('Неожиданные параметры видео')
    if Fraction(v['r_frame_rate']) != 60 or au['codec_name'] != 'aac':
        raise SystemExit('Ожидались 60 fps и AAC')
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-xerror', '-i', str(out), '-f', 'null', '-'], check=True)
    print('Created', out, flush=True)
    print(f'PROGRESS готово · {int((time.time() - t0) // 60)} мин', flush=True)


if __name__ == '__main__':
    main()
