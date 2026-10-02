"""The Century Dictionary and Cyclopedia (1897), as a book this engine builds.

Selected by this repository's ``book.env`` (``WIKIKIT_CORPUS=century:CENTURY``).

The first book with no Wikisource transcription: its text comes from its scans,
transcribed by our own vision model and proofread by a person.  The scans are
the University of California's complete ten-volume set on the Internet Archive,
scanned at 300 ppi — one library, one printing, every volume.  Volumes 1-8 are
the dictionary (A-Z), 9 the Cyclopedia of Names, 10 the Atlas.

``scan_name`` is each volume's Internet Archive identifier, not a Wikisource
DjVu file: the engine's Wikisource ``Page:`` addressing does not apply to this
book, and reading pages from the scans is engine work still to be built.
"""
from wikikit.corpora import Corpus

#: Volume -> its Internet Archive item.  Volume 10's identifier is spelled
#: differently by the scanning centre; it is the same set (UC, 1897, 300 ppi).
IA_ITEMS = {
    1: "centurydictionary01whit",
    2: "centurydictionary02whit",
    3: "centurydictionary03whit",
    4: "centurydictionary04whit",
    5: "centurydictionary05whit",
    6: "centurydictionary06whit",
    7: "centurydictionary07whit",
    8: "centurydictionary08whit",
    9: "centurydictionary09whit",
    10: "willcenturydicti10whit",
}

#: Scanned leaves per volume, from each item's Internet Archive metadata
#: (`imagecount`, 2026-10-02) — covers and blank leaves included.
_PAGES = {1: 916, 2: 918, 3: 916, 4: 908, 5: 902, 6: 904, 7: 916, 8: 890,
          9: 1110, 10: 904}


def _ia_item(volume: int) -> str:
    if volume not in IA_ITEMS:
        raise ValueError(f"the Century has volumes 1-10, not {volume}")
    return IA_ITEMS[volume]


CENTURY = Corpus(
    key="century",
    title="The Century Dictionary and Cyclopedia",
    scan_name=_ia_item,
    pages=_PAGES,
    raw_dir="century",
    derived_dir="data/derived",
    images_dir="data/images",
)
