"""Transcribe Century pages from their scans into supplied pages.

    uv run python tools/transcribe.py VOLUME PAGE [PAGE ...] [--force]

For each page: fetch its scan from the Internet Archive (cached in
data/scans/, never committed), cut it, locate its figures, read every text
item (`wikikit.scan`), write data/supplied/vol_NN/volNN-pagePPPP.json, and
regenerate its figure crops into data/images/.  A page already supplied is left
alone unless --force: its readings may hold a proofreader's corrections.
"""
from __future__ import annotations

import argparse
import sys

from century import scan_url
from century.scans import scan
from wikikit.scan import supplied

sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume", type=int)
    ap.add_argument("pages", type=int, nargs="+")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for page in a.pages:
        if supplied.path_for(a.volume, page).exists() and not a.force:
            print(f"vol {a.volume} p{page}: already supplied — left alone (--force to redo)")
            continue
        img = scan(a.volume, page)
        payload = supplied.transcribe_page(img, a.volume, page, scan_url(a.volume, page))
        path = supplied.write(payload)
        figs = supplied.materialize_figures(payload, img)
        p = payload["provenance"]
        print(f"vol {a.volume} p{page}: {len(p['items'])} items, {len(figs)} figures, "
              f"refused {p['refused'] or 'none'}, model/ink disagree {p['disagreements'] or 'nowhere'} -> {path}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
