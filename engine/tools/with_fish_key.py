"""Run a Python command with a new key entered invisibly; never writes the key to disk."""
import getpass
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python engine/tools/with_fish_key.py engine/tools/tts_takes.py projects/01-topic --voice VOICE_ID')
    key = getpass.getpass('Новый ключ Fish Audio (ввод скрыт; Enter — без озвучки): ').strip()
    env = os.environ.copy()
    env['FISH_API_KEY'] = key
    try:
        raise SystemExit(subprocess.run([sys.executable, '-B', *sys.argv[1:]], env=env).returncode)
    finally:
        env.pop('FISH_API_KEY', None)
        key = ''


if __name__ == '__main__':
    main()
