"""Readings worth a proofreader's second look, found from the book's own order
and notation — no model call.  Handed to the desk (`wikikit.scan.desk.bundle`,
`flags=`), which marks each span and says why.

A flag is a pointer, not a verdict: the page may well print what was read.

  order      A dictionary runs alphabetically.  A headword out of order between
             its neighbours is nearly always a misreading (or a lost strip).
  head       The running head prints the page's first and last headwords; a
             page whose readings begin or end elsewhere has a misread head or
             headword, or a strip that went missing.
  notation   A respelling may use only the marks of the book's pronunciation
             key (data/scan_notation.json).  A mark outside it is a misreading
             or a rarity.

An entry opens with its headword in bold at the start of a line, then any
superior figure, then its respelling in parentheses:
    '''aardvark''' (ärd′värk), ''n.'' [D., < ''aarde'' …
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

#: An entry's head: bold at a line's start, a superior figure, a respelling.
_ENTRY = re.compile(r"(?m)^(?:¶\n)?'''(?P<word>[^'\n]+?)'''(?:<sup>[^<]*</sup>)?"
                    r"(?:\s*\((?P<resp>[^()\n]{1,80})\))?")
#: Sense numbers are bold at a line's start too ('''1.'''): not headwords.
_SENSE = re.compile(r"^[\dIVXivx]+\.?$|^[a-z]\.$")
_RUNNING_HEAD = re.compile(r"^\{\{RunningHeader\|([^|{}]*)\|([^|{}]*)\|([^|{}]*)\}\}$")
#: Respelling punctuation and words the key does not list: stress marks, the
#: hyphen between syllables, space, comma, and "or" between alternatives.
_RESP_FURNITURE = set("′″- ,.") | {"or"}


def _key(word: str) -> str:
    """A headword as alphabetical order sees it: letters only, no accents, no case."""
    base = unicodedata.normalize("NFKD", word)
    return "".join(c for c in base if c.isalpha()).lower()


def _graphemes(text: str) -> list[str]:
    """Base characters with their combining marks, NFC."""
    out = []
    for c in unicodedata.normalize("NFD", text):
        if unicodedata.combining(c) and out:
            out[-1] += c
        else:
            out.append(c)
    return [unicodedata.normalize("NFC", g) for g in out]


def _key_marks() -> set[str]:
    path = Path("data/scan_notation.json")
    if not path.exists():
        return set()
    groups = json.loads(path.read_text(encoding="utf-8"))["groups"]
    marks = set()
    for g in groups:
        for s in g["symbols"]:
            marks.update(_graphemes(s["symbol"]))
    return marks


def _entries(payload: dict) -> list[dict]:
    """Every entry head on the page, in reading order: strip, offsets, word, respelling."""
    p = payload["provenance"]
    out = []
    for it in p["items"]:
        if it["kind"] != "text":
            continue
        text = p["readings"].get(it["name"], "")
        begins = text.lstrip().startswith("¶")
        for m in _ENTRY.finditer(text):
            word = m.group("word").strip().rstrip(".")
            if not any(c.isalpha() for c in word) or _SENSE.match(word):
                continue                      # a sense number, a homograph mark ("3†")
            if m.start() == 0 and not begins:
                continue                      # the strip continues a word or entry: no new entry
            if "\n" not in text[:m.start()] and not begins and text[:m.start()].strip():
                continue
            out.append({"strip": it["name"], "word": word, "start": m.start("word"), "end": m.end("word"),
                        "resp": m.group("resp"), "resp_at": m.start("resp") if m.group("resp") else None})
    return out


def page_flags(payload: dict) -> dict[str, list[dict]]:
    """{strip name: [{"text", "start", "end", "reason"}]} for one supplied page."""
    flags: dict[str, list[dict]] = {}

    def flag(strip: str, text: str, start: int, reason: str) -> None:
        flags.setdefault(strip, []).append({"text": text, "start": start, "end": start + len(text),
                                            "reason": reason})

    entries = _entries(payload)
    keys = [_key(e["word"]) for e in entries]

    # order: out of place between both neighbours
    for i, e in enumerate(entries):
        prev = keys[i - 1] if i > 0 else None
        nxt = keys[i + 1] if i + 1 < len(entries) else None
        k = keys[i]
        if prev is not None and nxt is not None and prev <= nxt and not (prev <= k <= nxt):
            flag(e["strip"], e["word"], e["start"],
                 f"out of alphabetical order: between “{entries[i - 1]['word']}” and “{entries[i + 1]['word']}”")

    # head: the guide words against the first and last headwords
    head = (payload["provenance"]["readings"].get("head") or "").strip()
    m = _RUNNING_HEAD.match(head)
    if m and entries:
        left, right = m.group(1).strip(), m.group(3).strip()
        # A page that opens mid-entry is headed by that entry's word, which
        # comes BEFORE the first headword; one that opens with an entry, by it.
        first = next((it["name"] for it in payload["provenance"]["items"] if it["kind"] == "text"), None)
        opens = (payload["provenance"]["readings"].get(first, "") or "").lstrip().startswith("¶")
        bad_left = (_key(left) != keys[0]) if opens else (_key(left) > keys[0])
        if left and bad_left:
            flag("head", left, head.index(left),
                 f"guide word “{left}”, but the page's first headword reads “{entries[0]['word']}”")
        if right and _key(right) != keys[-1]:
            flag("head", right, head.rindex(right),
                 f"guide word “{right}”, but the page's last headword reads “{entries[-1]['word']}”")

    # notation: every mark in a respelling is in the key
    allowed = _key_marks()
    if allowed:
        for e in entries:
            if not e["resp"]:
                continue
            pos = e["resp_at"]
            for g in _graphemes(e["resp"]):
                plain = unicodedata.normalize("NFC", g)
                ok = (g in allowed or g in _RESP_FURNITURE or (g.isascii() and g.isalpha()))
                if not ok:
                    flag(e["strip"], plain, pos, f"“{plain}” in a respelling is not in the pronunciation key")
                pos += len(plain)
    return flags
