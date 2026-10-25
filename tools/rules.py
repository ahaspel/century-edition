"""The book's own rules for its text (`century.rules`, `Corpus.text_rules`),
applied to the pages already read.  A page read, assembled or saved from now
on has them applied as it is written (`wikikit.scan.supplied.book_rules`);
this sets the pages written before a rule came.

    uv run python tools/rules.py [--write]
        -> each page whose body a rule changes, and how many characters; the
           total.  --write: write them.  Only the body changes: a page whose
           text would change anywhere else is refused, and nothing is written
           while any is.
"""
from __future__ import annotations

import sys
from pathlib import Path

from wikikit.scan import supplied
from wikikit.source_pages import SUPPLIED_DIR

sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    write = "--write" in sys.argv[1:]
    changed, refused = [], []
    for f in sorted(Path(SUPPLIED_DIR).glob("vol_*/*.json")):
        v, p = int(f.parent.name[4:]), int(f.stem[-4:])
        payload = supplied.read(v, p)
        raw = payload["raw_text"]
        head, body, furniture = supplied.page_parts(raw)
        level = supplied.level(payload)
        if supplied.framed(head, body, furniture, level) != raw:
            refused.append(f"{f.stem}: its text is not as framing writes it — set by hand?")
            continue
        new = supplied.book_rules(body)
        if new != body:
            payload["raw_text"] = supplied.framed(head, new, furniture, level)
            changed.append((payload, f"{f.stem}: +{len(new) - len(body)} characters"))
    for x in refused:
        print("REFUSED", x)
    for _, line in changed:
        print(line)
    print(f"{len(changed)} page(s) changed by the book's rules" + (f", {len(refused)} refused" if refused else ""))
    if refused and write:
        print("nothing written while a page is refused")
        return 1
    if write:
        for payload, _ in changed:
            supplied.write(payload)
        print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
