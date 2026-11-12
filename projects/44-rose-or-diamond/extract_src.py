"""Screen-recording frames for render.py: input/rubup_screen.mp4 -> build/src/NNNNNN.jpg (NNNNNN = round(s * 60)).
Only the source ranges used by timeline.SEG; crop y 230..1510 (status bar and Telegram header removed, the
«Крутить ещё» button kept), scale 1.5 -> 1080 x 1920 (the screen fills the frame; events.card_xy).
The recording is not in Git: Google Drive id 1vjGlk1za-mmJhg03_Y-pJB2t-e1ek8Tw (author, 2026-11-12), downloaded if missing."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'input' / 'rubup_screen.mp4'
OUT = HERE / 'build' / 'src'
RANGES = [(0.0, 8.2), (29.8, 34.0), (33.2, 44.4), (44.0, 52.0), (51.8, 58.52)]
DRIVE = 'https://drive.usercontent.google.com/download?id=1vjGlk1za-mmJhg03_Y-pJB2t-e1ek8Tw&export=download&confirm=t'
Y0 = 230


def cut(r):
    a, b = r
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', str(SRC),
                    '-vf', f'fps=60,crop=720:1280:0:{Y0},scale=1080:1920:flags=lanczos', '-q:v', '2',
                    '-start_number', str(round(a * 60)), str(OUT / '%06d.jpg')], check=True)


def scroll_measure():
    """List offset of the recording's own scroll (orig px, 30 fps, s 0–18.5) -> build/scrollP.npy for the smooth scroll."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-to', '18.5', '-i', str(SRC), '-vf',
                          'fps=30,crop=360:1000:180:420,scale=180:500,format=gray', '-f', 'rawvideo', '-'],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 500, 180).astype(np.float32)
    P = [0.0]
    for a, b in zip(f, f[1:]):
        best = min((np.mean(np.abs(a[dy + 20:480] - b[20:480 - dy])) if dy >= 0 else
                    np.mean(np.abs(a[20:480 + dy] - b[20 - dy:480])), dy) for dy in range(-10, 120))
        P.append(P[-1] + best[1])
    np.save(HERE / 'build' / 'scrollP.npy', np.array(P) * 2)


def spin_measure():
    """Reel offset of both case spins (orig px per 60 fps source frame) -> build/spin1X.npy, spin2X.npy: [times, X]."""
    import numpy as np
    for name, (a, b) in (('spin1', (33.3, 40.0)), ('spin2', (44.0, 52.8))):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', str(SRC), '-vf',
                              'fps=60,crop=720:240:0:640,scale=360:60,format=gray', '-f', 'rawvideo', '-'],
                             capture_output=True, check=True).stdout
        f = np.frombuffer(raw, np.uint8).reshape(-1, 60, 360).astype(np.float32)
        X = [0.0]
        for p, q in zip(f, f[1:]):
            best = min((np.mean(np.abs(p[:, dx + 20:340] - q[:, 20:340 - dx])) if dx >= 0 else
                        np.mean(np.abs(p[:, 20:340 + dx] - q[:, 20 - dx:340])), dx) for dx in range(-6, 140))
            X.append(X[-1] + best[1])
        np.save(HERE / 'build' / f'{name}X.npy', np.stack([a + np.arange(len(X)) / 60, np.array(X) * 2]))


if __name__ == '__main__':
    if not SRC.exists():
        subprocess.run(['curl', '-sSfL', '--retry', '5', '-o', str(SRC), DRIVE], check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(len(RANGES)) as ex:
        list(ex.map(cut, RANGES))
    print(len(list(OUT.glob('*.jpg'))), 'frames ->', OUT)
    scroll_measure()
    spin_measure()
