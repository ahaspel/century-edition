"""The Century's page scans: fetched from the Internet Archive once, cached in
data/scans/ (never committed)."""
from __future__ import annotations

import io
import time
from pathlib import Path

import requests
from PIL import Image

from century import scan_url

SCANS = Path("data/scans")
AGENT = {"User-Agent": "century-edition/0.1 (ahaspel@gmail.com)"}


def _whole(data: bytes) -> bool:
    """The image loads to its last byte: a download cut off short (vol 1
    leaf 641, 2026-11-20: "image file is truncated") is never cached."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.load()
        return True
    except OSError:
        return False


def scan(volume: int, page: int) -> Image.Image:
    path = SCANS / f"vol_{volume:02d}" / f"page{page:04d}.jpg"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            r = requests.get(scan_url(volume, page), headers=AGENT, timeout=180)
            r.raise_for_status()
            time.sleep(1)
            if _whole(r.content):
                break
        else:
            raise OSError(f"vol {volume} leaf {page}: the scan came cut off three times")
        # written whole or not at all: an interrupted write leaves no file
        part = path.with_suffix(".part")
        part.write_bytes(r.content)
        part.replace(path)
    return Image.open(path)
