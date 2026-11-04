"""Check source integrity; --distribution additionally audits the clean starter manifest."""
import argparse
import hashlib
import importlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'engine'))
EXCLUDED = {'.git', '.venv', 'venv', '__pycache__', '.cache', 'build', 'review', 'voice', 'renders', 'old-drafts', 'node_modules'}
MEDIA = {'input/video/RubUP Gifts banner.mov'} | {
    f'input/fonts/SF-Pro-Text/SF-Pro-Text-{weight}.otf'
    for weight in ('Regular', 'Medium', 'Semibold', 'Bold', 'Heavy')}
TEXT = {'.py', '.md', '.txt', '.json', '.example', '.gitignore', '.yml', '.yaml', '.toml', ''}


def files():
    for folder, directories, names in os.walk(ROOT):
        directories[:] = [d for d in directories if d not in EXCLUDED and d != 'keys']
        for name in names:
            if name == '.env' or name.startswith('.env.') and name != '.env.example':
                continue
            yield Path(folder) / name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distribution', action='store_true', help='Require exactly the original clean manifest and six allowed media')
    args = parser.parse_args()
    issues = []
    paths = list(files())
    for name in ('START_HERE.md', 'AGENTS.md', 'README.md', 'STYLE.md', 'STORY.md',
                 'docs/NEXT-STEPS.md', 'templates/project/STORYBOARD.md',
                 '.agents/skills/telegram-video/SKILL.md', 'requirements.txt', *sorted(MEDIA)):
        if not (ROOT / name).is_file():
            issues.append('Missing: ' + name)
    python_count = markdown_count = 0
    private_path = re.compile(r'(?i)(?:\b[A-Z]:[\\/](?:Users|Files|Apps)[\\/]|/(?:Users|home)/[^/\s]+/|\\\\[a-z0-9_-]+\\)')
    credentials = re.compile(r'''(?i)(?:api[_ -]?key|access[_ -]?token|password|secret)\s*[=:]\s*['"]?([A-Za-z0-9_.-]{16,})''')
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix not in TEXT and path.name != '.gitignore':
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeError:
            issues.append('Non-text file in source tree: ' + rel)
            continue
        if path.suffix == '.py':
            python_count += 1
            try:
                compile(text, rel, 'exec')
            except SyntaxError:
                issues.append('Python syntax: ' + rel)
        if private_path.search(text):
            issues.append('Personal or fixed host path: ' + rel)
        if credentials.search(text):
            issues.append('Possible credential assignment: ' + rel)
        if path.suffix == '.md':
            markdown_count += 1
            for link in re.findall(r'\[[^\]]*\]\(([^)\s]+)\)', text):
                if link.startswith(('http:', 'https:', '#', 'mailto:')):
                    continue
                destination = (path.parent / unquote(link.split('#')[0])).resolve()
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    issues.append('Broken or external local link: ' + rel)
    for module in ('paths', 'fx', 'captions', 'layout', 'raster', 'frames', 'gifts_api', 'lottie', 'sound', 'voice', 'banner'):
        try:
            importlib.import_module(module)
        except Exception as error:
            issues.append('Import ' + module + ': ' + type(error).__name__)
    if args.distribution:
        manifest_path = ROOT / 'DISTRIBUTION-MANIFEST.json'
        if not manifest_path.is_file():
            issues.append('Distribution manifest missing')
        else:
            expected = json.loads(manifest_path.read_text(encoding='utf-8'))['files']
            actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
            if actual != set(expected) | {'DISTRIBUTION-MANIFEST.json'}:
                issues.append('Distribution file set differs from manifest')
            for name, digest in expected.items():
                path = ROOT / name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    issues.append('Distribution checksum differs: ' + name)
            actual_media = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'input').rglob('*')
                            if p.is_file() and p.name != 'README.md'}
            if actual_media != MEDIA:
                issues.append('Media set must be the current banner and five SF Pro Text files only')
            for path in ROOT.rglob('*'):
                if path.is_symlink():
                    issues.append('Symlinks are not allowed in distribution')
                if path.is_dir() and (path.name in EXCLUDED - {'renders'} or path.name == 'keys'):
                    issues.append('Generated or secret directory in distribution')
                if path.is_file() and (path.name == '.env' or path.suffix in {'.pyc', '.log'}):
                    issues.append('Generated or secret file in distribution')
    print(f'Python: {python_count}; Markdown: {markdown_count}; imports checked')
    for issue in issues:
        print('FAIL:', issue)
    print('RESULT:', 'OK' if not issues else 'FAILED')
    raise SystemExit(1 if issues else 0)


if __name__ == '__main__':
    main()
