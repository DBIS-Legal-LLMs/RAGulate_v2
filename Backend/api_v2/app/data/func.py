import string, random, os
from pathlib import Path


PREFIX_FILE = "username_prefix.txt"
SUFFIX_FILE = "username_suffix.txt"

def _load_wordlist(path: str) -> list[str]:
    p = Path(os.path.join(os.path.dirname(__file__), path))
    if not p.exists():
        return []
    words: list[str] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                words.append(w[0].upper() + w[1:])
                #print("[DEBUG]: " + w)
    return words

PREFIX_WORDS = _load_wordlist(PREFIX_FILE)
SUFFIX_WORDS = _load_wordlist(SUFFIX_FILE)
NUMBER_CHARS = list(string.digits)

def get_username_parts():
    return PREFIX_WORDS, SUFFIX_WORDS, NUMBER_CHARS