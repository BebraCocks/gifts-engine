"""Approved full build: audio, frames, mux and decode verification. Never overwrites a final file."""
import argparse
from fractions import Fraction
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
sys.path.insert(0, str(Path(__file__).resolve().parent))
import doctor


def probe(path):
    result = subprocess.run([paths.ffprobe(), '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--approved', action='store_true', help='Use only after the author explicitly says «собирай»')
    parser.add_argument('--name', default='video_v1')
    args = parser.parse_args()
    if not args.approved:
        parser.error('Покажите хайлайты и дождитесь слова «собирай», затем добавьте --approved')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.name):
        parser.error('Output name must contain Latin letters, numbers, _ or -')
    project = Path(args.project).resolve()
    if project.parent != paths.PROJECTS:
        parser.error('Choose a project directly under projects/')
    if not doctor.ensure():
        raise SystemExit(1)
    out = paths.RENDERS / project.name / (args.name + '.mp4')
    if out.exists():
        parser.error('Final file exists; use --name with a new version')
    out.parent.mkdir(parents=True, exist_ok=True)
    build = paths.build(project)
    for command in ([sys.executable, '-B', 'audio.py'],
                    [sys.executable, '-B', 'render.py', '--video', str(build / 'video_only.mp4')]):
        subprocess.run(command, cwd=project, check=True)
    mix = build / 'mix.wav'
    if not mix.is_file():
        raise SystemExit('Audio missing: the banner must keep its sound')
    subprocess.run([paths.ffmpeg(), '-n', '-v', 'error', '-i', str(build / 'video_only.mp4'),
                    '-i', str(mix), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-ar', '48000', '-map_metadata', '-1', '-movflags', '+faststart', str(out)], check=True)
    info = probe(out)
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    if (video['width'], video['height'], video['pix_fmt'], video['codec_name']) != (1080, 1920, 'yuv420p', 'h264'):
        raise SystemExit('Unexpected video delivery parameters')
    if Fraction(video['r_frame_rate']) != 60 or audio['codec_name'] != 'aac':
        raise SystemExit('Expected 60 fps and AAC audio')
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-xerror', '-i', str(out), '-f', 'null', '-'], check=True)
    print('Created renders/' + project.name + '/' + out.name)
    print('Decoded successfully. Now review movement, transitions and full audio by eye and ear.')


if __name__ == '__main__':
    main()
