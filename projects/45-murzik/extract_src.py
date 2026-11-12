"""Screen-recording frames for render.py: input/rubup_screen.mp4 -> build/src/NNNNNN.jpg (NNNNNN = round(s * 60)).
Only the source ranges used by timeline.SEG; crop y 230..1510 (status bar and Telegram header removed),
scale 1.5 -> 1080 x 1920 (the screen fills the frame; events.card_xy).
The recording «rubup 3» is not in Git: Google Drive id 1Iy-WH_MbPD4u-XVkiRp8Lsh6nr1hQK50 (author, 2026-11-12), downloaded if missing."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'input' / 'rubup_screen.mp4'
OUT = HERE / 'build' / 'src'
RANGES = [(0.0, 1.4), (4.3, 15.9), (15.9, 25.2), (25.4, 34.1), (41.0, 43.3), (46.8, 51.4), (51.0, 64.7)]
DRIVE = 'https://drive.usercontent.google.com/download?id=1Iy-WH_MbPD4u-XVkiRp8Lsh6nr1hQK50&export=download&confirm=t'
Y0 = 230


def cut(r):
    a, b = r
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', str(SRC),
                    '-vf', f'fps=60,crop=720:1280:0:{Y0},scale=1080:1920:flags=lanczos', '-q:v', '2',
                    '-start_number', str(round(a * 60)), str(OUT / '%06d.jpg')], check=True)


if __name__ == '__main__':
    if not SRC.exists():
        subprocess.run(['curl', '-sSfL', '--retry', '5', '-o', str(SRC), DRIVE], check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(cut, RANGES))
    print(len(list(OUT.glob('*.jpg'))), 'frames ->', OUT)
