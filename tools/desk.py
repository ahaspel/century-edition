"""The proofreading desk's data for the Century, through wikikit.scan.desk.

    uv run python tools/desk.py bundle VOLUME PAGE [PAGE ...]
        -> data/derived/desk/: desk.json, strip images, desk_render.js, and
           seed/<strip id>.json, one document per text strip for the desk's store
    uv run python tools/desk.py apply DIR
        DIR holds the desk's saved strips, one <strip id>.json each
        (as exported from its store): readings corrected, checks recorded,
        pages reassembled
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from century.scans import scan
from wikikit.scan import desk

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path("data/derived/desk")


def bundle(volume: int, pages: list[int]) -> None:
    keys = [(volume, p) for p in pages]
    path = desk.bundle(keys, {k: scan(*k) for k in keys}, OUT)
    shutil.copyfile(desk.DESK_RENDER_JS, OUT / "desk_render.js")
    seed = OUT / "seed"
    shutil.rmtree(seed, ignore_errors=True)
    seed.mkdir()
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for pg in data["pages"]:
        for s in pg["strips"]:
            if s["kind"] == "figure":
                continue
            (seed / f"{s['id']}.json").write_text(json.dumps({
                "page": pg["id"], "name": s["name"], "text": s["text"], "model_text": s["text"],
                "status": "checked" if s["checked"] else "unchecked"},
                ensure_ascii=False), encoding="utf-8")
            n += 1
    print(f"{path}: {len(data['pages'])} pages, {n} text strips to seed")


def apply(src: Path) -> None:
    rows = {}
    for f in sorted(src.glob("*.json")):
        rows[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    for line in desk.apply(rows):
        print(line)


def main() -> int:
    if len(sys.argv) >= 4 and sys.argv[1] == "bundle":
        bundle(int(sys.argv[2]), [int(p) for p in sys.argv[3:]])
    elif len(sys.argv) == 3 and sys.argv[1] == "apply":
        apply(Path(sys.argv[2]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
