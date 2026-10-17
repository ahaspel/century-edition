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


#: The first leaf of each volume's text (read from its scans, 2026-10-17):
#: before it, the binding, endpapers, blank leaves, title pages, and the lists
#: of abbreviations and the key to pronunciation — what a contributor's run
#: (tools/contribute.py) does not read.  Volume 1's front matter (its preface)
#: and the lists are for later (user, 2026-10-17).  Volume 9, the Cyclopedia
#: of Names, opens with its own preface (leaves 11-13) and a blank leaf.
#: Volume 10, the Atlas, is maps and their indexes, not read as text: not set,
#: so a run there is refused.
TEXT_STARTS = {1: 27, 2: 13, 3: 13, 4: 13, 5: 13, 6: 13, 7: 13, 8: 13, 9: 15}


def _ia_item(volume: int) -> str:
    if volume not in IA_ITEMS:
        raise ValueError(f"the Century has volumes 1-10, not {volume}")
    return IA_ITEMS[volume]


def scan_url(volume: int, page: int) -> str:
    """The full-resolution image of one page.  Pages are numbered from 1, as
    Wikisource numbers a DjVu's pages; the Internet Archive numbers its leaves
    from 0 — page N is leaf n(N-1)."""
    if not 1 <= page <= _PAGES[volume]:
        raise ValueError(f"volume {volume} has pages 1-{_PAGES[volume]}, not {page}")
    return f"https://archive.org/download/{_ia_item(volume)}/page/n{page - 1}.jpg"


def _page_scan(volume: int, page: int):
    """`century.scans.scan`, imported when a transcription asks for a page
    (that module imports this one)."""
    from century.scans import scan
    return scan(volume, page)


CENTURY = Corpus(
    key="century",
    title="The Century Dictionary and Cyclopedia",
    scan_name=_ia_item,
    pages=_PAGES,
    raw_dir="century",
    derived_dir="data/derived",
    images_dir="data/images",
    # The site: under a path of the author's own host (user, 2026-10-03), so
    # every address the engine writes starts with /century (`Corpus.root`).
    site="https://reference.aaronhaspel.com/century",
    # What the transcriber is told about this book: its key to pronunciation
    # (vol. 1 p. xviii), and its pages in its own words.
    data_files=frozenset({"scan_notation.json", "templates/scan_page.md"}),
    # Every page is transcribed from its Archive scan.
    page_scan=_page_scan,
    page_scan_url=scan_url,
    # The book prints its quotation marks and apostrophes curly (user,
    # 2026-10-17); our readings mostly typed them straight (vol. 1 p. 9,
    # ''abducted'' … "''enlevé''"), and a straight ' beside '' is the markup's
    # own character.  Set curly as each page is read, and any straight pair a
    # proofreader types set curly in the edition.
    curly_quotes=True,
    curly_readings=True,
)
