"""Text-only timeline: authored times from events.py (no voice takes in this clip)."""
import config
from events import DUR, HEROES_T, HOOK_T, FINAL_T

HAS_NARRATION = False if config.WITHOUT_NARRATION else False
TAKES = []
ON = [HOOK_T[0][0], HOOK_T[1][0]] + [h['title'] for h in HEROES_T] + [FINAL_T['line1']]
END = [HOOK_T[0][1], HOOK_T[1][1]] + [h['out'] for h in HEROES_T] + [DUR - 0.3]
