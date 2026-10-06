# Transcribing the Century on your own API key

Thank you for helping.  You transcribe pages from the scans with Claude, on your
own Anthropic API key and within a budget you set; the pages come back to the
project as files in a pull request.  Nothing else of yours is used or sent.

## Once: set up

You need **git**, and **uv** (which brings the right Python with it):
<https://docs.astral.sh/uv/getting-started/installation/>.

Clone the two repositories **side by side** in one folder — the book uses the
engine from `../wikikit`:

```
mkdir century-work && cd century-work
git clone https://github.com/ahaspel/wikikit.git
git clone https://github.com/ahaspel/century-edition.git
cd century-edition
uv sync
```

Put your key in a file named `.env` in `century-edition` (it is never committed):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then check that it works (this costs a fraction of a cent):

```
uv run python tools/contribute.py check
```

## Each time: transcribe some pages

You are assigned a volume, so no two people read the same pages.  Choose how
much to spend on this run:

```
uv run python tools/contribute.py run --volume 8 --budget 25 --dry-run   # see what $25 buys
uv run python tools/contribute.py run --volume 8 --budget 25 --wait     # do it
```

The pages go through Anthropic's Batch API — half the normal price; answers
usually come within an hour, at most a day.  `--wait` keeps the command running
until they are done.  Without it, the command sends the batch and exits: run
`uv run python tools/contribute.py run --wait` later to collect.

A run never takes you past `--monthly-cap` (default $200) for the calendar
month, counted from what your runs actually cost on this machine.  The
estimate per page is the average of the pages already done.

## Hand the pages back

```
uv run python tools/contribute.py send
```

This commits the new pages on your own branch (`contrib/<your git name>`),
pushes it, and prints a link to open a pull request — once; later sends add to
the same pull request.  Only the page files go: scans and figure crops are
rebuilt from the Internet Archive.

## Good to know

- Your key never leaves `.env`, which git ignores.  Never paste it anywhere else.
- A page the model declines, or reads badly, is not lost: it is marked in the
  page file and listed for a person to transcribe.
- If something stops with an error, the run's state is kept
  (`data/derived/scan_batch/`): fix the cause and run again — finished pages are
  never paid for twice.
- Questions about a reading belong on the proofreading desk, as a comment on
  the strip.
