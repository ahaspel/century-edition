"""The Century's page scans: fetched from the Internet Archive once, cached in
data/scans/ (never committed)."""
from __future__ import annotations

import time
from pathlib import Path

import requests
from PIL import Image

from century import scan_url

SCANS = Path("data/scans")
AGENT = {"User-Agent": "century-edition/0.1 (ahaspel@gmail.com)"}


def scan(volume: int, page: int) -> Image.Image:
    path = SCANS / f"vol_{volume:02d}" / f"page{page:04d}.jpg"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(scan_url(volume, page), headers=AGENT, timeout=180)
        r.raise_for_status()
        path.write_bytes(r.content)
        time.sleep(1)
    return Image.open(path)
