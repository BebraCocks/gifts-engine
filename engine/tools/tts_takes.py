"""Create optional narration takes for a project; preserves all existing takes."""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fish_tts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--voice', default=os.environ.get('FISH_VOICE'))
    parser.add_argument('--takes', type=int, default=1)
    parser.add_argument('--speed', type=float, default=1.0)
    args = parser.parse_args()
    if args.takes < 1:
        parser.error('--takes must be positive')
    project = Path(args.project).resolve()
    if not fish_tts.available() or not args.voice:
        print('Нужны новый ключ Fish Audio и выбранный вами голос. Добавите их? Пока работаем без дикторской озвучки.')
        return
    spec = importlib.util.spec_from_file_location('narration_script', project / 'script.py')
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    folder = project / 'voice'
    folder.mkdir(exist_ok=True)
    manifest = folder / 'takes.json'
    log = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    for line, data in enumerate(script.LINES, 1):
        for take in range(1, args.takes + 1):
            name = f'L{line:02d}_take{take:02d}'
            out = folder / f'{name}.wav'
            if out.exists():
                print(name, 'уже есть — сохранён')
                continue
            fish_tts.tts(data[0], out, args.voice, speed=args.speed)
            log[name] = {'engine': 'fish', 'model': os.environ.get('FISH_TTS_MODEL', 's2.1-pro'),
                         'voice': args.voice, 'speed': args.speed, 'text': data[0]}
            manifest.write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(name, 'готов; прослушайте и выберите дубль')
    print('Выбранные дубли скопируйте в voice/L01.wav, L02.wav… без удаления остальных.')


if __name__ == '__main__':
    main()
