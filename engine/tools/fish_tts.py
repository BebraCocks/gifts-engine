"""Optional Fish Audio narration. Reads only FISH_API_KEY from the process environment."""
import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API = 'https://api.fish.audio'
# Author's default narration voice and model (2026-11-04); env vars override them.
DEFAULT_VOICE = '7312c38557eb4fb384e3874e8e9cea67'
DEFAULT_MODEL = 'drama-3'


def default_voice():
    return os.environ.get('FISH_VOICE') or DEFAULT_VOICE


def available():
    return bool(os.environ.get('FISH_API_KEY', '').strip())


def _request(method, endpoint, body=None):
    key = os.environ.get('FISH_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Fish Audio key is absent; continue without narration')
    headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
               'model': os.environ.get('FISH_TTS_MODEL') or DEFAULT_MODEL}
    request = urllib.request.Request(API + endpoint, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        # Do not print response bodies, request headers or credentials.
        raise RuntimeError(f'Fish Audio HTTP {error.code}') from None
    except urllib.error.URLError:
        raise RuntimeError('Fish Audio network request failed') from None


def fix_wav_sizes(data):
    """Replace streaming WAV size placeholders with actual PCM sizes."""
    data = bytearray(data)
    i = 12
    while i + 8 <= len(data):
        chunk, size = data[i:i+4], int.from_bytes(data[i+4:i+8], 'little')
        if chunk == b'data':
            size = (len(data) - i - 8) // 2 * 2
            del data[i+8+size:]
            data[i+4:i+8] = size.to_bytes(4, 'little')
            break
        i += 8 + size + size % 2
    data[4:8] = (len(data) - 8).to_bytes(4, 'little')
    return bytes(data)


def voices():
    return json.loads(_request('GET', '/model?page_size=20&language=ru&licensed=true')).get('items', [])


def tts(text, out_path, voice, speed=1.0):
    if not voice:
        raise ValueError('Choose a voice for the new account first')
    out = Path(out_path)
    if out.exists():
        raise FileExistsError('Voice take already exists; choose a new file name')
    body = {'text': text, 'reference_id': voice, 'format': 'wav', 'sample_rate': 44100,
            'normalize': True, 'prosody': {'speed': speed}}
    data = _request('POST', '/v1/tts', json.dumps(body, ensure_ascii=False).encode('utf-8'))
    if data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        raise RuntimeError('Fish Audio did not return WAV audio')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('xb') as stream:
        stream.write(fix_wav_sizes(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    sub.add_parser('voices')
    say = sub.add_parser('say')
    say.add_argument('out')
    say.add_argument('text')
    say.add_argument('--voice', default=default_voice())
    args = parser.parse_args()
    if not available():
        print('Нет нового ключа Fish Audio. Добавите свой ключ? Пока продолжаем без дикторской озвучки.')
        return
    if args.command == 'check':
        voices()
        print('Fish Audio: доступ подтверждён; ключ не выводится')
    elif args.command == 'voices':
        for item in voices():
            print(item.get('_id'), item.get('title', ''))
    else:
        tts(args.text, args.out, args.voice)
        print('Новая реплика сохранена')


if __name__ == '__main__':
    main()
