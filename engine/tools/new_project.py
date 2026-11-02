"""Create one neutral project from the maintained template."""
import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='For example: 01-topic')
    args = parser.parse_args()
    if not re.fullmatch(r'\d{2,}-[a-z0-9]+(?:-[a-z0-9]+)*', args.name):
        parser.error('Use a number and lowercase Latin words, for example 01-topic')
    target = ROOT / 'projects' / args.name
    if target.exists():
        parser.error('Project already exists; choose another name')
    shutil.copytree(ROOT / 'templates' / 'project', target)
    print('Created projects/' + args.name + '. Start with STORYBOARD.md and your own style brief.')


if __name__ == '__main__':
    main()
