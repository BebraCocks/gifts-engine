"""Screen-recording frames for render.py: input/rubup_screen.mp4 -> build/src/NNNNNN.jpg (NNNNNN = round(s * 60)).
Only the source ranges used by timeline.SEG; crop y 190..1440, scale 1.05 -> 756 x 1313 (events.CARD_*).
The recording is not in Git (>100 MB): Google Drive id 1vIYnVwsDUp9DktYtv4KcpxQmDNISQ40H, downloaded if missing."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'input' / 'rubup_screen.mp4'
OUT = HERE / 'build' / 'src'
RANGES = [(9.0, 23.0), (35.0, 59.0), (93.0, 103.2), (140.8, 160.27)]
DRIVE = 'https://drive.usercontent.google.com/download?id=1vIYnVwsDUp9DktYtv4KcpxQmDNISQ40H&export=download&confirm=t'


def cut(r):
    a, b = r
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', str(SRC),
                    '-vf', 'fps=60,crop=720:1250:0:190,scale=756:1313:flags=lanczos', '-q:v', '2',
                    '-start_number', str(round(a * 60)), str(OUT / '%06d.jpg')], check=True)


if __name__ == '__main__':
    if not SRC.exists():
        subprocess.run(['curl', '-sSfL', '--retry', '5', '-o', str(SRC), DRIVE], check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(len(RANGES)) as ex:
        list(ex.map(cut, RANGES))
    print(len(list(OUT.glob('*.jpg'))), 'frames ->', OUT)
