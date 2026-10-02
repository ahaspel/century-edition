# Working in this repo

This is a BOOK repository.  The engine is wikikit, checked out at `../wikikit`;
engine changes are committed THERE, everything else here — say which
repository, every time.  The sister books are `../britannica-edition` (EB1911,
whose `CLAUDE.md` and `docs/status.md` hold the working history) and
`../dnb-edition`.

- **The text comes from the scans.**  There is no Wikisource transcription.
  Our own vision model transcribes; a person proofreads.  Never the scans' OCR
  text layer.
- **Standard Wikisource markup only** — the vocabulary the engine's producers
  already handle, so a transcribed page runs through them unchanged.  A
  template the engine does not know is a transcription error, not a new
  producer.
- **Transcribe what is printed.**  Never correct, modernise or complete; the
  book's own notation (its pronunciation key) is the book's data.
- **The engine never asks which book it is building.**  A Century fact belongs
  in this repository's profile (`src/century`) or a hook it names.
- **Bash only, never PowerShell.  Never put Python in a heredoc** — write the
  script to a file and run it.
- **The user runs `git commit`.**  Draft the message in the console; never
  commit unless told so in that turn.
- `.env` holds credentials: never print it, and filter settings errors, which
  echo their input.
