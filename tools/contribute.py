"""Transcribe the Century piecemeal, on your own API key, within a budget.

    uv run python tools/contribute.py check                       # key works? where are we?
    uv run python tools/contribute.py run --volume 8 --budget 25  # next pages, up to $25
    uv run python tools/contribute.py run --wait                  # advance a run until done
    uv run python tools/contribute.py run --volume 8 --budget 25 --direct   # read them now
    uv run python tools/contribute.py send                        # hand the finished pages back

Your key goes in `.env` at the repository root (never committed):

    ANTHROPIC_API_KEY=sk-ant-...

`run` picks the next pages of your volume that nobody has transcribed, from
the first page of its text on (`century.TEXT_STARTS`: never the binding,
blank leaves or title pages before it), fetching the repository first so it
sees what others have sent; it estimates
their cost from what pages have actually cost so far, and sends as many as the
budget allows through the Batch API (half price; answered within a day,
usually much sooner).  A spending ledger (data/derived/contrib_ledger.json,
local) keeps each month's actual cost; a run that would pass --monthly-cap is
refused.  `run --wait` polls until the batch is done and writes the pages to
data/supplied/; without --wait, run it again later to collect.

`run --direct` reads the same pages now, one call at a time, at the standard
rate (twice the batch price) — for a key whose route does not carry the Batch
API (`check` says whether yours does).  Each page is written as soon as it is
read and booked in the ledger at once, so stopping it loses nothing; the
estimate, the budget and the cap are at the price actually paid.

`send` commits the new pages on a branch of their own and pushes it; open a
pull request from it (the command prints where).  Only the page files go:
scans and figure crops are rebuilt from the Internet Archive.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from century import CENTURY, TEXT_STARTS, scan_url
from century.scans import scan
from wikikit.scan import batch, supplied
from wikikit.scan.model import MODEL, USAGE_FIELDS

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "derived" / "contrib_ledger.json"
#: Batch prices, US$ per million tokens (half the standard rate): checked
#: against the Anthropic pricing page when this was written; update with it.
PRICE = {"input_tokens": 2.5, "output_tokens": 12.5,
         "cache_read_input_tokens": 0.25, "cache_creation_input_tokens": 3.125}
#: A page read now pays the standard rate.
STANDARD = 2
#: Until real pages have been measured: a dense three-column dictionary page.
FALLBACK_PER_PAGE = 0.20


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def own_branch() -> str:
    """The contributor's one long-lived branch, `contrib/<their git name>`:
    every page they transcribe stays in their checkout, `send` pushes it, and
    what the maintainer has accepted is merged back in by `run`."""
    who = git("config", "user.name") or "contributor"
    slug = "".join(c if c.isalnum() else "-" for c in who.lower()).strip("-")
    return f"contrib/{slug}"


def maintainer() -> bool:
    """This checkout is the maintainer's (`git config century.maintainer true`,
    local, never committed): their pages are read where they stand, on master,
    never on a contributor's branch."""
    return git("config", "--bool", "--default", "false", "century.maintainer") == "true"


def on_own_branch() -> str:
    branch = own_branch()
    if git("branch", "--show-current") != branch:
        exists = branch in git("branch", "--list", branch)
        git("switch", "-q", branch) if exists else git("switch", "-q", "-c", branch)
    return branch


def cost(usage: dict, batched: bool | None = None) -> float:
    """What a page's calls cost: at the rate each record says it was read at
    (a record without the word was read now — the engine marked only batches
    once), or, given `batched`, at that rate whatever the record says."""
    total = 0.0
    for part in usage.values():
        if not isinstance(part, dict):
            continue
        b = part.get("batch", False) if batched is None else batched
        total += sum(part.get(f, 0) * PRICE[f] for f in PRICE) * (1 if b else STANDARD)
    return total / 1e6


def per_page_estimate(batched: bool = True) -> float:
    """Average cost of the pages already transcribed, at the rate this run
    will pay: the tokens a page takes do not depend on the route."""
    costs = [cost(json.loads(f.read_text(encoding="utf-8"))["provenance"].get("usage", {}), batched)
             for f in (ROOT / "data" / "supplied").glob("vol_*/*.json")]
    costs = [c for c in costs if c > 0]
    if len(costs) >= 5:
        return sum(costs) / len(costs)
    return FALLBACK_PER_PAGE * (1 if batched else STANDARD)


def book(spent_now: float) -> float:
    """Add to this month's ledger; the month's total."""
    led = ledger()
    led[month()] = round(led.get(month(), 0.0) + spent_now, 4)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, indent=1), encoding="utf-8")
    return led[month()]


def ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}


def month() -> str:
    return dt.date.today().strftime("%Y-%m")


def done_pages(volume: int) -> set[int]:
    return {int(f.stem[-4:]) for f in (ROOT / "data" / "supplied" / f"vol_{volume:02d}").glob("*.json")}


def check(_a) -> int:
    from wikikit.settings import settings
    if settings.anthropic_api_key is None:
        print("No API key: put ANTHROPIC_API_KEY=... in .env at the repository root.")
        return 1
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    try:
        client.messages.create(model=MODEL, max_tokens=5, messages=[{"role": "user", "content": "Say OK."}])
        print(f"API key works with {MODEL}.")
    except Exception as e:                          # say why, never the key
        print(f"The API refused: {type(e).__name__}: {getattr(e, 'message', e)}")
        return 1
    try:                                            # read-only: lists, sends nothing
        client.messages.batches.list(limit=1)
        print("The Batch API is open to this key: `run` sends batches at half price.")
    except Exception as e:
        print(f"The Batch API is not open to this key ({type(e).__name__}): use `run --direct`.")
    spent = ledger().get(month(), 0.0)
    print(f"Spent this month (this machine): ${spent:.2f}.  Estimated cost per page: "
          f"${per_page_estimate():.3f} by batch, ${per_page_estimate(batched=False):.3f} direct.")
    state = batch.load()
    waiting = [p for p in state["pages"].values() if p["stage"] != "done"]
    print(f"A run in progress: {len(waiting)} page(s) not yet done." if waiting else "No run in progress.")
    return 0


def pick(a, batched: bool) -> tuple[list[int], float, float] | int:
    """The next pages of the volume nobody has transcribed (or waits on in a
    batch), as many as the budget buys at this run's rate: (pages, the
    estimate a page, the budget) — or an exit code when there is nothing to do."""
    if a.volume is None or a.budget is None:
        print("Give --volume and --budget to start pages.")
        return 1
    if not maintainer():
        on_own_branch()
    git("fetch", "-q", "origin")
    git("merge", "-q", "--no-edit", "origin/master")             # see what others have sent
    spent = ledger().get(month(), 0.0)
    budget = min(a.budget, a.monthly_cap - spent)
    if budget <= 0:
        print(f"This month's cap is reached (${spent:.2f} of ${a.monthly_cap:.2f}).")
        return 1
    each = per_page_estimate(batched)
    waiting = {(p["volume"], p["page"]) for p in batch.load()["pages"].values() if p["stage"] != "done"}
    if a.volume not in TEXT_STARTS:
        print(f"Where volume {a.volume}'s text begins is not yet set (century.TEXT_STARTS): nothing sent.")
        return 1
    todo = [p for p in range(TEXT_STARTS[a.volume], CENTURY.pages[a.volume] + 1)
            if p not in done_pages(a.volume) and (a.volume, p) not in waiting]
    take = todo[:max(0, int(budget // each))]
    if not take:
        print(f"Budget ${budget:.2f} buys no page at ~${each:.3f}." if todo else f"Volume {a.volume} is finished.")
        return 0
    print(f"Volume {a.volume}: pages {take[0]}-{take[-1]} ({len(take)} pages, ~${len(take) * each:.2f}"
          f"{'' if batched else ', read now at the standard rate'}).")
    if a.dry_run:
        print("Dry run: nothing sent.")
        return 0
    return take, each, budget


def run_direct(a) -> int:
    """Read the pages now, one call at a time: each written and booked as soon
    as it is read, so an interruption or a refusal from the API loses nothing
    already paid for.  Stops before a page the rest of the budget may not cover."""
    picked = pick(a, batched=False)
    if isinstance(picked, int):
        return picked
    take, each, budget = picked
    paid, done = 0.0, 0
    for page in take:
        if paid + each > budget:
            print(f"Stopping: ${budget - paid:.2f} left may not cover another page (~${each:.3f}).")
            break
        try:
            img = scan(a.volume, page)
            payload = supplied.transcribe_page(img, a.volume, page, scan_url(a.volume, page))
        except Exception as e:                      # say why, never the key
            print(f"p{page}: not read — {type(e).__name__}: {getattr(e, 'message', e)}.  "
                  f"Stopping; run again to go on from here.")
            break
        supplied.write(payload)
        supplied.materialize_figures(payload, img)
        c = cost(payload["provenance"]["usage"])
        paid += c
        done += 1
        total = book(c)
        p = payload["provenance"]
        flags = "".join([f"; refused {p['refused']}" if p["refused"] else "",
                         f"; unread {sorted(p['unread'])}" if p["unread"] else ""])
        print(f"p{page}: ${c:.3f}{flags}  (this run ${paid:.2f}, this month ${total:.2f})", flush=True)
    if done:
        print(f"{done} page(s) written to data/supplied/, costing ${paid:.2f}.  Run `send` to hand them back.")
    return 0


def run(a) -> int:
    if a.direct:
        return run_direct(a)
    state = batch.load()
    open_pages = [p for p in state["pages"].values() if p["stage"] != "done" and not p.get("error")]
    if not open_pages:
        picked = pick(a, batched=True)
        if isinstance(picked, int):
            return picked
        batch.add_pages([(a.volume, p, scan_url(a.volume, p)) for p in picked[0]], scan)
    before = {pid for pid, p in batch.load()["pages"].items() if p["stage"] == "done"}
    if a.wait:
        batch.run_until_done(scan, log=lambda s: print(s, flush=True))
    else:
        print(json.dumps(batch.advance(scan), default=str, indent=1))
    state = batch.load()
    finished = [p for pid, p in state["pages"].items() if p["stage"] == "done" and pid not in before]
    if finished:
        spent_now = sum(cost(p["usage"]) for p in finished)
        total = book(spent_now)
        print(f"{len(finished)} page(s) written to data/supplied/, costing ${spent_now:.2f}; "
              f"this month ${total:.2f}.  Run `send` to hand them back.")
    errors = {pid: p["error"] for pid, p in state["pages"].items() if p.get("error")}
    if errors:
        print("Set aside with an error (they are not lost; tell the maintainer):", errors)
    return 0


def send(_a) -> int:
    branch = on_own_branch()
    new = git("status", "--porcelain", "--", "data/supplied").splitlines()
    if new:
        git("add", "data/supplied")
        git("commit", "-q", "-m", f"Transcribed pages ({len(new)} files) with {MODEL}")
    ahead = git("rev-list", "--count", f"origin/master..{branch}") if git("branch", "-r", "--list", "origin/master") else "?"
    if not new and ahead in ("0", ""):
        print("No new pages to send.")
        return 0
    # the proofreading desk commits to this branch too (its saves, and the
    # pages it sends into the book): take those first, ours on top
    if git("ls-remote", "--heads", "origin", branch):
        git("pull", "-q", "--rebase", "origin", branch)
    git("push", "-q", "-u", "origin", branch)
    url = git("remote", "get-url", "origin").removesuffix(".git")
    print(f"Sent: branch {branch} is pushed ({len(new)} new page file(s) in this commit).\n"
          f"If no pull request is open for it yet, open one: {url}/compare/{branch}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run")
    r.add_argument("--volume", type=int, choices=range(1, 10))
    r.add_argument("--budget", type=float, help="dollars to spend on this run")
    r.add_argument("--monthly-cap", type=float, default=200.0)
    r.add_argument("--wait", action="store_true", help="poll until the batch is done")
    r.add_argument("--direct", action="store_true",
                   help="read the pages now, at the standard rate, not through the Batch API")
    r.add_argument("--dry-run", action="store_true", help="show the pages and the estimate; send nothing")
    sub.add_parser("send")
    a = ap.parse_args()
    return {"check": check, "run": run, "send": send}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
