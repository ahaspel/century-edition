"""The proofreading desk's data for the Century, through wikikit.scan.desk.

The desk proofreads a page at a time: the whole scan beside the page's text,
as one text to correct, and one check for the page.  Each page is proofread by
whoever fetched it on their own key, until it is given to someone else at the
desk (`supplied.owner`); the desk shows each person their own.

    uv run python tools/desk.py bundle [--each N] [VOL:PAGE[-PAGE] ...]
        -> data/derived/desk/: each person's next N pages not yet proofread
           (default 20), in the book's order, and any pages named besides
           (8:13-17: vol 8 leaves 13 to 17): desk.json, page scans, figure
           copies, desk_render.js, and seed/<page id>.json, one document per
           page for the desk's store.  Apply the desk's saved pages FIRST: a
           page given away at the desk is the new owner's only once applied.
    uv run python tools/desk.py apply DIR
        DIR holds the desk's saved pages, one <page id>.json each (as
        exported from its store): each page takes its text as the
        proofreader left it, proofread once they checked it
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from century.scans import scan
from century.flags import page_flags
from wikikit.scan import desk, supplied

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path("data/derived/desk")


_HEAD = re.compile(r"^\{\{RunningHeader\|([^|{}]*)\|([^|{}]*)\|([^|{}]*)\}\}$")


def _head(volume: int, page: int):
    if not supplied.path_for(volume, page).exists():
        return None
    m = _HEAD.match(supplied.page_parts(supplied.read(volume, page)["raw_text"])[0].strip())
    return m if m and m.group(2).strip().isdigit() else None


def label(volume: int, page: int) -> str:
    """The page as the book numbers it, from its running head (the printed
    number and guide words) — or, on a page printed without one (the first
    of a letter), from the next page's."""
    m = _head(volume, page)
    if m:
        return f"Vol. {volume}, p. {m.group(2).strip()} ({m.group(1).strip()} – {m.group(3).strip()})"
    after = _head(volume, page + 1)
    return f"Vol. {volume}, p. {int(after.group(2)) - 1}" if after else f"Vol. {volume}, leaf {page}"


def _pages() -> list[tuple[int, int]]:
    return sorted((int(f.parent.name[4:]), int(f.stem[-4:]))
                  for f in Path(supplied.path_for(1, 1)).parent.parent.glob("vol_*/*.json"))


def people() -> list[str]:
    """Everyone a page may be given to: whoever has fetched or been given one."""
    return sorted({o for k in _pages() if (o := supplied.owner(supplied.read(*k)))})


def next_pages(each: int) -> list[tuple[int, int]]:
    """Each person's next `each` pages not yet proofread, in the book's order."""
    taken: dict[str, list] = {}
    for k in _pages():
        payload = supplied.read(*k)
        who = supplied.owner(payload)
        if who and supplied.level(payload) < 3 and len(taken.setdefault(who, [])) < each:
            taken[who].append(k)
    return sorted(k for ks in taken.values() for k in ks)


def bundle(keys: list[tuple[int, int]]) -> None:
    for sub in ("pages", "figures", "seed", "strips"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
    path = desk.bundle(keys, {k: scan(*k) for k in keys}, OUT, flags=page_flags, label=label,
                       people=people())
    shutil.copyfile(desk.DESK_RENDER_JS, OUT / "desk_render.js")
    seed = OUT / "seed"
    seed.mkdir()
    data = json.loads(path.read_text(encoding="utf-8"))
    for pg in data["pages"]:
        (seed / f"{pg['id']}.json").write_text(json.dumps({
            "head": pg["head"], "text": pg["text"],
            "model_head": pg["head"], "model_text": pg["text"],
            "status": "checked" if pg["checked"] else "unchecked", "owner": pg["owner"]},
            ensure_ascii=False), encoding="utf-8")
    files = [f for f in OUT.rglob("*") if f.is_file() and f.parts[len(OUT.parts)] in ("pages", "figures")]
    print(f"{path}: {len(data['pages'])} pages, {len(files)} images, "
          f"{sum(f.stat().st_size for f in files) / 1e6:.1f} MB")
    for who in data["people"]:
        mine = [pg["label"] for pg in data["pages"] if pg["owner"] == who]
        print(f"  {who}: {len(mine)} page(s)" + (f", {mine[0]} to {mine[-1]}" if mine else ""))


def apply(src: Path) -> None:
    rows = {}
    for f in sorted(src.glob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        rows[f.stem] = doc.get("data", doc)
    for line in desk.apply_pages(rows) or ["no page changed"]:
        print(line)


def main() -> int:
    if sys.argv[1:2] == ["bundle"]:
        args, each, named = sys.argv[2:], 20, set()
        if args[:1] == ["--each"]:
            each, args = int(args[1]), args[2:]
        for a in args:
            vol, _, pages = a.partition(":")
            first, _, last = pages.partition("-")
            named |= {(int(vol), p) for p in range(int(first), int(last or first) + 1)}
        bundle(sorted(set(next_pages(each)) | named))
    elif len(sys.argv) == 3 and sys.argv[1] == "apply":
        apply(Path(sys.argv[2]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
