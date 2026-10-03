"""Transcribe Century pages from their scans into supplied pages.

    uv run python tools/transcribe.py VOLUME PAGE [PAGE ...] [--force]
    uv run python tools/transcribe.py VOLUME PAGE [PAGE ...] --batch [--wait]
    uv run python tools/transcribe.py --batch [--wait]        # just advance the run

For each page: fetch its scan from the Internet Archive (cached in
data/scans/, never committed), cut it, locate its figures, read every text
item (`wikikit.scan`), write data/supplied/vol_NN/volNN-pagePPPP.json, and
regenerate its figure crops into data/images/.  A page already supplied is left
alone unless --force: its readings may hold a proofreader's corrections.

--batch sends the same calls through the Batch API (half the price, answered
within a day): the pages join the run in data/derived/scan_batch/, one step is
taken, and the tool exits; run it again (or with --wait, which polls every few
minutes) until every page is done.
"""
from __future__ import annotations

import argparse
import json
import sys

from century import scan_url
from century.scans import scan
from wikikit.scan import batch, supplied

sys.stdout.reconfigure(encoding="utf-8")


def report(payload: dict, figs: list) -> str:
    p = payload["provenance"]
    return (f"vol {payload['volume']} p{payload['page_number']}: {len(p['items'])} items, "
            f"{len(figs)} figures, refused {p['refused'] or 'none'}, unread {p['unread'] or 'none'}, "
            f"model/ink disagree {p['disagreements'] or 'nowhere'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume", type=int, nargs="?")
    ap.add_argument("pages", type=int, nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    todo = []
    for page in a.pages:
        if supplied.path_for(a.volume, page).exists() and not a.force:
            print(f"vol {a.volume} p{page}: already supplied — left alone (--force to redo)")
        else:
            todo.append(page)

    if a.batch:
        batch.add_pages([(a.volume, p, scan_url(a.volume, p)) for p in todo], scan)
        if a.wait:
            batch.run_until_done(scan)
        else:
            print(json.dumps(batch.advance(scan), default=str, indent=1))
        return 0

    for page in todo:
        img = scan(a.volume, page)
        payload = supplied.transcribe_page(img, a.volume, page, scan_url(a.volume, page))
        path = supplied.write(payload)
        figs = supplied.materialize_figures(payload, img)
        print(f"{report(payload, figs)} -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
