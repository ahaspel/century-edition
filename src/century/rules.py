"""The Century's own rules for its text (`Corpus.text_rules`): each takes a
reading or a page's text and gives it as the book sets it, and changes
nothing it has already set, so a rule runs wherever text is written — as a
page is read, as it is assembled, as a proofreader's save comes in.

ETYMOLOGY SPACING (user, 2026-10-25): an entry's etymology, the bracket that
follows its headword, pronunciation and grammar, is set off by two word
spaces at each end ("affectate (a-fek′tāt), a.  [< L. affectatus …
affect¹.]  Affected"); our readings set one, and HTML collapses two.  Set
as THREE of ours (user, 2026-10-25: two "really looks like one"): the
print's word spaces, on its justified lines, are about half an em, so its
gap is 1.1-1.6 em (vol. 1 p. 124: 30px against word gaps of 14px; 43
against 22); ours are a quarter em, and two of them make one of the
print's.  Two no-break spaces (U+00A0, which do not collapse: written as
characters, the desk's text shows the gap) and the plain space after them,
where a line may break.

CITATIONS (user, 2026-10-25): a prose citation opens with a paragraph
indent, and nothing else in small type does — synonyms (vol. 1 p. 38),
notes (p. 42), sub-entries (p. 35) are flush.  Its source is set flush
right, on its last line when it fits (p. 200, "Beverley, Virginia, i. ¶ 93."),
else on a line of its own.  The book's CSS sets both; the text has to say
which small blocks are citations, and says it so: one citation to a
{{smaller block}}, ending in its source in {{right|…}}.  A block our reading
gave several citations is split after each source; a source read run in is
set in {{right|…}}.  A citation broken by the page is one block once the
pages are joined (`preprocess`: small type fused at the seam).

SOURCES IN A DEFINITION (user, 2026-10-25): a source given without a
citation, closing a definition, is set off by two spaces, as an etymology is
("…signification of terms of art or the professions.  Warton.", vol. 8
p. 6209; "…of New South Wales.  A. H. Garrod, 1875.", vol. 1 p. 119).  Not
a source after an example quoted in the definition, which follows at a word
space ("…“soar airwards again,” Thackeray, Shabby-Genteel Story, iv.", p. 151);
not one the definition goes on after ("Abroad. Burns. Also spelled abraid.",
p. 44: the print does not show it).
"""
from __future__ import annotations

import re

#: an entry: its headword in bold, opening a line (the page's first behind
#: its {{nop}}; some behind the book's ¶) or following a quotation's close on
#: its line — never a sense's number ('''2.''', '''II.''', '''1'''†, '''4†.''')
_ENTRY = re.compile(r"(?:^|\n|\}\} )(?:\{\{nop\}\})?(?:¶ ?)?'''(?![\dIVXLC]+†?\.?''')[^'\n]+'''")
#: what an entry's head holds between its headword and its etymology, set
#: aside to see whether anything else is left: bold and italic runs (more
#: headwords, the part of speech, inflections), the pronunciation and other
#: parentheses, superscripts, templates
_HEAD_PARTS = re.compile(r"'''.*?'''|''.*?''|\([^()\n]*\)|<sup>.*?</sup>|\{\{[^{}\n]*\}\}")
#: the head's own words, outside those: abbreviations (pret., pp., ppr., pl.,
#: adv.), joining words, numbers
_HEAD_WORD = re.compile(r"(?:[^\W\d_]+\.)+|and|or|as|also|of|the|same|in|with|used|\d+", re.I)
SPACE = "  "
SMALL = "{{smaller|"


def _brackets(text: str, start: int) -> int | None:
    """Where the [ at `start` closes, counting brackets inside it and never
    a link's [[ ]]; None if it does not close in `text`."""
    depth = 0
    i = start
    while i < len(text):
        if text.startswith("[[", i) or text.startswith("]]", i):
            i += 2
            continue
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def etymology_at(text: str, entry_end: int) -> int | None:
    """The [ that opens the etymology of the entry whose headword ends at
    `entry_end`: the first bracket in its paragraph with nothing before it
    but the head (`_HEAD_PARTS`, `_HEAD_WORD`, punctuation) — never a label
    after a definition ("neighbor. [Rare.]"), never a bracket in a quotation
    or on a later line.  None when the entry has none."""
    end = text.find("\n", entry_end)
    line = text[entry_end:end if end >= 0 else len(text)]
    k = next((i for i, c in enumerate(line) if c == "[" and not line.startswith("[[", i)
              and not (i and line[i - 1] == "[")), None)
    if k is None:
        return None
    # the obsolete mark † (after a headword, or an inflection: "pl.†") is the
    # head's own; an etymology set small opens inside its {{smaller|
    head = line[:k].removesuffix(SMALL)
    rest = _HEAD_PARTS.sub(" ", head.replace(SPACE, " ")).replace("†", " ").replace("‡", " ")
    words = re.findall(r"[^\s,;:.]+\.?", rest)
    if any(not _HEAD_WORD.fullmatch(w) for w in words):
        return None
    return entry_end + k


def etymology_spacing(text: str) -> str:
    """Two word spaces at each end of each entry's etymology (module doc)."""
    out, last = [], 0
    for m in _ENTRY.finditer(text):
        if m.start() < last:
            continue
        a = etymology_at(text, m.end())
        if a is None:
            continue
        b = _brackets(text, a)
        # set small: the spaces go outside {{smaller|[ … ]}}
        if text[:a].endswith(SMALL):
            a -= len(SMALL)
            if b is not None and text.startswith("}}", b + 1):
                b += 2
        # before the [: a space, not already set
        if text[a - 1:a] == " " and not text[:a - 1].endswith(SPACE):
            out.append(text[last:a - 1] + SPACE)
            last = a - 1
        # after the ]: a space before the definition, not already set (an
        # etymology running on to the next page closes there, unset: the rule
        # sees one page, and a ] at a page's top may close a quotation's note)
        if b is not None and text[b + 1:b + 2] == " " and not text.startswith(SPACE, b + 1):
            out.append(text[last:b + 1] + SPACE)
            last = b + 1
    out.append(text[last:])
    return "".join(out)


BLOCK = "{{smaller block|"
#: a right-set line, a template or two inside it
_RIGHT = re.compile(r"\{\{right\|(?:[^{}]|\{\{[^{}]*\}\})*\}\}")
#: a source read run in at a citation's end — after the sentence's close
#: (its last word in italic or not; on the line or the next), the author in
#: italic, then the work after a comma ("''Chapman'', Iliad.", "''Shak.,''
#: M. W. of W."), or the author alone, the italic closing on his period
#: ("''Gresley.''")
_RUN_IN = re.compile(r"(?:(?<=[.!?”’)—])|(?<=[.!?,”’]''))[ \n]+"
                     r"(''[A-Z][^'\n]{0,40}(?:'',|,'')[^\n{}]{0,100}|''[A-Z][^'\n]{0,40}\.'')$")
#: what opens a small block that is no citation: a poem (its own source run
#: in is the verse's line), a synonym paragraph, a note, a sub-entry
_NOT_PROSE = ("<poem>", "=", "[", "'''")


def _template_end(text: str, start: int) -> int | None:
    """The end of the {{…}} opening at `start`, braces counted; None if it
    does not close in `text` (a block the page breaks)."""
    depth, i = 0, start
    while i < len(text) - 1:
        if text.startswith("{{", i):
            depth, i = depth + 1, i + 2
        elif text.startswith("}}", i):
            depth, i = depth - 1, i + 2
            if depth == 0:
                return i
        else:
            i += 1
    return None


def _source_set_right(piece: str) -> str:
    """A prose citation whose source was read run in, the source set right."""
    if piece.lstrip().startswith(_NOT_PROSE) or _RIGHT.search(piece):
        return piece
    body = piece.rstrip()
    m = _RUN_IN.search(body)
    if not m:
        return piece
    return body[:m.start()] + "\n{{right|" + m.group(1) + "}}" + piece[len(body):]


#: a source closing a definition: after a sentence's close (never a quoted
#: example's ”), the author in italic — alone, the period his own or after
#: ("''Warton.''", "''Bailey''.") or the work after a comma ("''Elyot'',
#: Dict.") — and then the definition's end: the line's, a label ("[Rare.]"),
#: the next sense ("—'''2.'''")
_DEF_SOURCE = re.compile(r"(?:(?<=[.!?;:)])|(?<=[.!?]''))( )"
                         r"(?=(?:''[A-Z][^'\n]{0,40}\.''|''[A-Z][^'\n]{0,40}''\.|"
                         r"''[A-Z][^'\n]{0,40}(?:'',|,'')[^\n\[\]{}—]{0,90}?)"
                         r"[  ]*(?:\n|$|\[|—|<))")


def _outside_quotations(text: str) -> list[tuple[int, int]]:
    """The stretches of `text` outside its small blocks (citations, notes),
    its brackets (etymologies, labels) and its entries' heads up to their
    etymologies (inflections after an abbreviation's period, "pp.
    ''Africanized'', ppr. ''Africanizing''.", vol. 1 p. 130): where a
    definition's own words stand."""
    shut = [(m.start(), a) for m in _ENTRY.finditer(text) if (a := etymology_at(text, m.end())) is not None]
    i = 0
    while (i := text.find(BLOCK, i)) >= 0:
        e = _template_end(text, i) or len(text)
        shut.append((i, e))
        i = e
    i = 0
    while (i := text.find("[", i)) >= 0:
        if text.startswith("[[", i) or text[i - 1:i] == "[":
            i += 1
            continue
        e = _brackets(text, i)
        e = len(text) if e is None else e + 1
        shut.append((i, e))
        i = e
    out, at = [], 0
    for a, b in sorted(shut):
        if a > at:
            out.append((at, a))
        at = max(at, b)
    out.append((at, len(text)))
    return out


def source_spacing(text: str) -> str:
    """Two word spaces before a source closing a definition (module doc)."""
    out, last = [], 0
    for a, b in _outside_quotations(text):
        for m in _DEF_SOURCE.finditer(text, a, b):
            out.append(text[last:m.start(1)] + SPACE)
            last = m.start(1)
    out.append(text[last:])
    return "".join(out)


def one_citation_per_block(text: str) -> str:
    """Each prose citation in a {{smaller block}} of its own, ending in its
    source set right (module doc)."""
    out, last, i = [], 0, 0
    while (i := text.find(BLOCK, i)) >= 0:
        end = _template_end(text, i)
        if end is None:
            break
        inner = text[i + len(BLOCK):end - 2]
        pieces, start = [], 0
        for m in _RIGHT.finditer(inner):
            after = inner[m.end():].lstrip()
            # another citation follows this one's source (not a second line
            # of the source, set right as well; never inside a poem, whose
            # source may stand on its last line: vol. 1 p. 170)
            in_poem = inner.count("<poem>", 0, m.end()) > inner.count("</poem>", 0, m.end())
            if after and not after.startswith("{{right|") and not in_poem:
                pieces.append(inner[start:m.end()])
                start = m.end()
        pieces.append(inner[start:])
        pieces = [pieces[0]] + [p.lstrip("\n ") for p in pieces[1:]]
        out.append(text[last:i] + "\n".join(BLOCK + _source_set_right(p) + "}}" for p in pieces))
        last = i = end
    out.append(text[last:])
    return "".join(out)
