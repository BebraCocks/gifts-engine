"""Check portable dependencies without collecting host identity or saving reports."""
import argparse
import importlib
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths


def ensure(verbose=True):
    errors = []
    if sys.version_info < (3, 10):
        errors.append('Python >= 3.10 required')
    for module in ('numpy', 'PIL', 'scipy', 'av', 'rlottie_python'):
        try:
            importlib.import_module(module)
        except ImportError:
            errors.append('Missing dependency: ' + module)
    for name, getter in (('ffmpeg', paths.ffmpeg), ('ffprobe', paths.ffprobe)):
        try:
            tool = getter()
            result = subprocess.run([tool, '-version'], capture_output=True, timeout=20)
            if result.returncode:
                errors.append(name + ' cannot start')
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            errors.append(name + ' unavailable; add to PATH or set its environment variable')
    try:
        result = subprocess.run([paths.ffmpeg(), '-v', 'error', '-f', 'lavfi', '-i',
                                 'color=s=64x64:d=0.05', '-c:v', 'libx264', '-f', 'null', '-'],
                                capture_output=True, timeout=20)
        if result.returncode:
            errors.append('FFmpeg libx264 is unavailable')
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        pass
    for weight in ('Regular', 'Medium', 'Semibold', 'Bold', 'Heavy'):
        try:
            paths.font(f'SF-Pro-Text-{weight}.otf')
        except FileNotFoundError:
            errors.append('Missing SF Pro Text: ' + weight)
    if not (paths.VIDEO_IN / 'RubUP Gifts banner.mov').is_file():
        errors.append('Missing current RubUp banner')
    if verbose:
        for error in errors:
            print('FAIL:', error)
        print('Environment:', 'READY' if not errors else 'NOT READY')
        print('Fish Audio is optional. Without a new key narration is skipped; banner sound remains.')
    return not errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--online', action='store_true', help='Check only an explicitly supplied new Fish Audio key')
    args = parser.parse_args()
    ok = ensure()
    if args.online:
        import fish_tts
        if fish_tts.available():
            try:
                fish_tts.voices()
                print('Fish Audio: OK')
            except RuntimeError as error:
                print(error)
                ok = False
        else:
            print('Нет нового ключа Fish Audio. Добавите свой ключ? Пока без дикторской озвучки.')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
