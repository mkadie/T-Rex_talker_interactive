"""Tiny INI-ish config loader for stim-game side-car .cfg files.

Same format as .menu files (see menu_parser.py) but with a narrower
parser: lines are `key = value`, blanks and # comments are ignored,
and a single `[section]` marker starts a new list-of-dicts group.

Example:
    title = AAC Trainer
    rounds = 10
    penalty_seconds = 30

    [question]
    prompt = sounds/trainer/thirsty.mp3
    answer = thirsty

    [question]
    prompt = sounds/trainer/hungry.mp3
    answer = hungry
"""


def _coerce(raw):
    val = raw.strip()
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def load(path):
    """Parse a .cfg file.

    Returns:
        (header, sections) where
          header   = dict of top-level key=value pairs (before any [section])
          sections = dict of section_name -> list of dicts
    """
    header = {}
    sections = {}
    current = header
    current_name = None

    try:
        f = open(path, "r")
    except OSError:
        return header, sections

    try:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_name = line[1:-1].strip()
                current = {}
                sections.setdefault(current_name, []).append(current)
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            current[k.strip()] = _coerce(v)
    finally:
        f.close()

    return header, sections
