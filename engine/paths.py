"""Project-relative paths. No host-specific lookup or external credentials are loaded."""
import os
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
INPUT = ROOT / "input"
IMAGES = INPUT / "images"
MODELS = INPUT / "models"
VIDEO_IN = INPUT / "video"
FONTS = INPUT / "fonts"
PROJECTS = ROOT / "projects"
RENDERS = ROOT / "renders"
CACHE = ROOT / ".cache"

def enter(script_file):
    here = Path(script_file).resolve().parent
    os.chdir(here)
    return here

def build(project_dir=None):
    d = Path(project_dir or Path.cwd()) / "build"
    d.mkdir(parents=True, exist_ok=True)
    return d

def font(name):
    hits = sorted(FONTS.rglob(name))
    if not hits:
        raise FileNotFoundError(f"Font missing: {name}")
    return str(hits[0])

def _tool(name):
    custom = os.environ.get(name.upper())
    exe = custom or shutil.which(name)
    if not exe or not Path(exe).is_file():
        raise RuntimeError(f"Install {name} and add it to PATH, or set {name.upper()}")
    return exe

def ffmpeg():
    return _tool("ffmpeg")

def ffprobe():
    return _tool("ffprobe")
