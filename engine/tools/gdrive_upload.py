"""Upload a finished video to the author's Google Drive folder «TikTok» (rule in AGENTS.md, 2026-11-06).

    python -B engine/tools/gdrive_upload.py renders/NN-topic/name_vN.mp4 [--folder FOLDER_ID]

Preferred: the author's Google Apps Script web app (it runs as the author and writes to the folder):
    GDRIVE_WEBHOOK_URL, GDRIVE_WEBHOOK_KEY — POST {key, name, data(base64)} -> {id, url}. Limit ≈ 50 MB per file.
Fallback, Drive API (credentials only from the process environment, never written to the repository or printed):
    GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN   — OAuth client of the author + refresh token
        (scope https://www.googleapis.com/auth/drive); a fresh access token is requested on every run;
    or GDRIVE_ACCESS_TOKEN — a short-lived access token (≈ 1 hour), for a one-off upload.
Resumable upload in 8 MB chunks; prints the file id and the view link. Exit code 2 when no credentials are set."""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FOLDER = '1NoVDLARcwDpyyvthn2D2klxIi_Tm1MAt'      # «TikTok», anyone with the link can view
CHUNK = 8 * 1024 * 1024


def access_token():
    if all(os.environ.get(k) for k in ('GDRIVE_CLIENT_ID', 'GDRIVE_CLIENT_SECRET', 'GDRIVE_REFRESH_TOKEN')):
        body = urllib.parse.urlencode({'client_id': os.environ['GDRIVE_CLIENT_ID'],
                                       'client_secret': os.environ['GDRIVE_CLIENT_SECRET'],
                                       'refresh_token': os.environ['GDRIVE_REFRESH_TOKEN'],
                                       'grant_type': 'refresh_token'}).encode()
        with urllib.request.urlopen('https://oauth2.googleapis.com/token', body, timeout=60) as r:
            return json.load(r)['access_token']
    if os.environ.get('GDRIVE_ACCESS_TOKEN'):
        return os.environ['GDRIVE_ACCESS_TOKEN']
    print('Нет ключей Google Drive: загрузка не выполнена.', file=sys.stderr)
    sys.exit(2)


def upload_webhook(path):
    body = json.dumps({'key': os.environ['GDRIVE_WEBHOOK_KEY'], 'name': path.name,
                       'data': base64.b64encode(path.read_bytes()).decode()}).encode()
    req = urllib.request.Request(os.environ['GDRIVE_WEBHOOK_URL'], data=body, method='POST',
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as r:          # Apps Script answers via a 302 -> GET
        text = r.read().decode('utf-8', 'replace')
    try:
        res = json.loads(text)
    except ValueError:
        sys.exit(f'Apps Script не принял файл: {text[:200]}')
    print(f'{path.name} -> {res["id"]}  {res["url"]}')
    return res


def upload(path, folder):
    if os.environ.get('GDRIVE_WEBHOOK_URL') and os.environ.get('GDRIVE_WEBHOOK_KEY') and folder == FOLDER:
        return upload_webhook(path)
    tok = access_token()
    size = path.stat().st_size
    meta = json.dumps({'name': path.name, 'parents': [folder]}).encode()
    req = urllib.request.Request(
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=id,webViewLink',
        data=meta, method='POST',
        headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json; charset=UTF-8',
                 'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
    with urllib.request.urlopen(req, timeout=60) as r:
        session = r.headers['Location']
    with open(path, 'rb') as f:
        pos = 0
        while pos < size:
            chunk = f.read(CHUNK)
            end = pos + len(chunk) - 1
            req = urllib.request.Request(session, data=chunk, method='PUT', headers={
                'Content-Length': str(len(chunk)), 'Content-Range': f'bytes {pos}-{end}/{size}'})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    res = json.load(r)                       # 200/201: done
                    print(f'{path.name} -> {res["id"]}  {res.get("webViewLink", "")}')
                    return res
            except urllib.error.HTTPError as e:
                if e.code != 308:                            # 308 = chunk accepted, continue
                    raise
            pos = end + 1
            print(f'  {pos * 100 // size}%', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--folder', default=FOLDER)
    a = ap.parse_args()
    for f in a.files:
        upload(Path(f), a.folder)
