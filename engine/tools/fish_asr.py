"""Fish Audio speech recognition with word timestamps. Reads only FISH_API_KEY from the environment.

    python engine/tools/fish_asr.py projects/02-x/voice/L01_take01.wav ...
Writes <take>.asr.json next to each file (text + word segments in seconds) and prints the text.
Use it to check that performance tags were not read aloud and to time captions by real speech.
Machine transcription supports, but does not replace, listening to the takes.
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = 'https://api.fish.audio/v1/asr'


def transcribe(path, language='ru'):
    key = os.environ.get('FISH_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Fish Audio key is absent')
    b = uuid.uuid4().hex
    head = ''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
                   for k, v in (('language', language), ('ignore_timestamps', 'false')))
    body = (head + f'--{b}\r\nContent-Disposition: form-data; name="audio"; filename="take.wav"\r\n'
            'Content-Type: audio/wav\r\n\r\n').encode() + Path(path).read_bytes() + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(API, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'multipart/form-data; boundary=' + b})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Fish Audio ASR HTTP {error.code}') from None


def cached(path):
    out = Path(str(path)[:-4] + '.asr.json')
    if out.exists():
        return json.loads(out.read_text(encoding='utf-8'))
    data = transcribe(path)
    data = {'text': data.get('text', ''), 'segments': data.get('segments', [])}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return data


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, cached(p)['text'])
