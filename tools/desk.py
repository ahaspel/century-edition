"""The proofreading desk for the Century, through wikikit.scan.desk.

The desk proofreads a page at a time: the whole scan beside the page's text,
as one text to correct, and one check for the page.  It is a static page on
GitHub Pages, one per person (desk/<person>/), each showing that person's next
pages not yet proofread from their own branch (`desk/people.json`: person ->
branch).  A save at the desk commits the page as the person left it to
`desk/inbox/<page id>.json` on their branch; "Send" commits `desk/send.json`,
and the desk workflow (.github/workflows/desk.yml) applies the inbox to
data/supplied, commits it to the branch, and rebuilds every person's desk.

    uv run python tools/desk.py site OUT PERSON BRANCH [--each N] [--send-id ID]
        -> OUT: PERSON's next N pages not yet proofread (default 20), from the
           first page of the text on (`century.TEXT_STARTS`), in the book's
           order: desk.json, page scans, figure copies, desk_render.js, the
           desk (tools/desk.html, as index.html) and site.json (whose desk it
           is, and the send it answers)
    uv run python tools/desk.py index OUT
        -> OUT/index.html: the list of everyone's desks
    uv run python tools/desk.py apply SRC [VOL:PAGE[-PAGE] ...]
        SRC is a folder of saved pages, one <page id>.json each (the desk's
        inbox), or a file {"pages": {<page id>: row}}: each page takes its
        text as the proofreader left it, proofread once they checked it.
        Pages named (8:18-23) limit it to those
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from century import TEXT_STARTS
from century.scans import scan
from century.flags import page_flags
from wikikit.scan import desk, supplied

sys.stdout.reconfigure(encoding="utf-8")
#: The desk itself: published as each person's index.html.
PAGE = Path(__file__).with_name("desk.html")
#: The repository the desk commits to (the desk reads it from site.json).
REPO = "ahaspel/century-edition"


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


def waiting(who: str) -> list[tuple[int, int]]:
    """`who`'s pages not yet proofread, in the book's order, from the first
    page of the text on: the front matter waits until the text is done."""
    return [k for k in _pages() if k[1] >= TEXT_STARTS.get(k[0], 1)
            and (p := supplied.read(*k)) and supplied.owner(p) == who and supplied.level(p) < 3]


def site(out: Path, person: str, branch: str, each: int, send_id: str | None) -> None:
    pending = waiting(person)
    keys = pending[:each]
    shutil.rmtree(out, ignore_errors=True)
    path = desk.bundle(keys, {k: scan(*k) for k in keys}, out, flags=page_flags, label=label,
                       people=[person])
    shutil.copyfile(desk.DESK_RENDER_JS, out / "desk_render.js")
    shutil.copyfile(PAGE, out / "index.html")
    built = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out / "site.json").write_text(json.dumps({
        "repo": REPO, "branch": branch, "person": person, "built_at": built,
        "send_id": send_id, "waiting": len(pending)}, indent=1), encoding="utf-8")
    labels = [pg["label"] for pg in json.loads(path.read_text(encoding="utf-8"))["pages"]]
    print(f"{person} ({branch}): {len(keys)} of {len(pending)} waiting"
          + (f", {labels[0]} to {labels[-1]}" if labels else ""))


def index(out: Path) -> None:
    people = json.loads(Path("desk/people.json").read_text(encoding="utf-8"))
    rows = "\n".join(f'<li><a href="{html.escape(p)}/">{html.escape(p)}</a></li>' for p in sorted(people))
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1\">"
        "<title>Century Proofreading Desk</title>"
        "<style>body{font:17px/1.5 system-ui,sans-serif;margin:2em 16px;max-width:40em}</style>"
        f"<h1>Century Proofreading Desk</h1><p>Whose desk?</p><ul>{rows}</ul>", encoding="utf-8")


def named_pages(args: list[str]) -> set[tuple[int, int]]:
    """VOL:PAGE[-PAGE] arguments -> {(vol, leaf)}: 8:13-17 is vol 8 leaves 13 to 17."""
    named = set()
    for a in args:
        vol, _, pages = a.partition(":")
        first, _, last = pages.partition("-")
        named |= {(int(vol), p) for p in range(int(first), int(last or first) + 1)}
    return named


def apply(src: Path, only: set[tuple[int, int]] | None = None) -> None:
    rows = {}
    if src.is_file():
        rows = json.loads(src.read_text(encoding="utf-8"))["pages"]
    else:
        for f in sorted(src.glob("*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            rows[f.stem] = doc.get("data", doc)
    if only:
        rows = {pid: row for pid, row in rows.items() if (int(pid[1:3]), int(pid[5:9])) in only}
        missing = {supplied.page_id(v, p) for v, p in only} - set(rows)
        if missing:
            print("not in the export:", ", ".join(sorted(missing)))
    for line in desk.apply_pages(rows) or ["no page changed"]:
        print(line)


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["site"] and len(args) >= 4:
        out, person, branch, rest = Path(args[1]), args[2], args[3], args[4:]
        opts = dict(zip(rest[::2], rest[1::2]))
        site(out, person, branch, int(opts.get("--each", 20)), opts.get("--send-id") or None)
    elif args[:1] == ["index"] and len(args) == 2:
        index(Path(args[1]))
    elif args[:1] == ["apply"] and len(args) >= 2:
        apply(Path(args[1]), named_pages(args[2:]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
