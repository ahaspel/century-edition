# century-edition

*The Century Dictionary and Cyclopedia* (1897) — the dictionary in eight
volumes, the Cyclopedia of Names and the Atlas — as a faithful digital edition,
transcribed from its scans and built by [wikikit](https://github.com/ahaspel/wikikit).

This repository is the BOOK: its profile (`src/century`), its data and its own
tools.  The engine lives in wikikit, which never asks which book it is
building.  Sister projects:
[britannica-edition](https://github.com/ahaspel/britannica-edition) and
dnb-edition.

**Source:** the University of California's complete ten-volume set on the
Internet Archive, scanned at 300 ppi (`centurydictionary01whit` …
`centurydictionary09whit`, `willcenturydicti10whit`).

**Status:** started 2026-10-02.  The Century has no Wikisource transcription,
so its text is made here: each page is cut into strips (column by column, in
the white space between lines), transcribed by a vision model into standard
Wikisource markup, and proofread by a person.

## Setup

wikikit is a local editable checkout beside this one:

    D:/work/wikikit        (or wherever — see [tool.uv.sources])
    D:/work/century-edition

Then:

    uv sync
    uv run pytest
