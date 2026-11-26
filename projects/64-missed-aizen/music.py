"""Music bed of episode 1: «Блич — Тема боя 2» (трек автора, input/music/, не в Git), громкость 20 % (автор).
Обрыв перед «Нет» в чате (M4) и возврат после паузы; затухание в конце. Build: python -B music.py"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRACK = ROOT / "input" / "music" / "bleach_battle_theme_2.mp3"
VOLUME = 0.20
OFFSET = 0.0  # с какого места трека начинаем


def build():
    cues = json.loads((HERE / "voice_cues.json").read_text())
    total = cues["total"]
    m4 = next(c for c in cues["cues"] if c["id"] == "M4")
    cut0, cut1 = m4["start"] - 0.45, m4["end"] + 0.9  # тишина вокруг «Нет»
    vol = (f"volume='{VOLUME}*if(lt(t,{cut0 - 0.25:.2f}),1,if(lt(t,{cut0:.2f}),({cut0:.2f}-t)/0.25,"
           f"if(lt(t,{cut1:.2f}),0,if(lt(t,{cut1 + 1.2:.2f}),(t-{cut1:.2f})/1.2,1))))':eval=frame")
    flt = f"atrim={OFFSET}:{OFFSET + total},asetpts=PTS-STARTPTS,{vol},afade=t=out:st={total - 1.5:.2f}:d=1.5"
    rev = HERE / "build" / "review"
    music = rev / "music_only.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(TRACK), "-af", flt, "-ar", "48000", "-ac", "2", str(music)],
                   check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(rev / "voice_only.mp3"), "-i", str(music), "-filter_complex",
                    "[0]aresample=48000,pan=stereo|c0=c0|c1=c0[v];[v][1]amix=inputs=2:normalize=0,alimiter=limit=0.95",
                    "-b:a", "192k", str(rev / "mix.mp3")], check=True)
    print(rev / "mix.mp3", f"silence {cut0:.2f}-{cut1:.2f}")


if __name__ == "__main__":
    build()
