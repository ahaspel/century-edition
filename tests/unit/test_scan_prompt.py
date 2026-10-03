"""What the transcriber is told about the Century: its own words and its key."""
import json

from century import CENTURY
from wikikit.scan.cut import Item
from wikikit.scan.transcribe import prompt_for


def test_the_prompt_carries_the_books_page_description_and_every_key_symbol():
    p = prompt_for(Item("text", (0, 0, 10, 10), 1, "c1s1"))
    assert "Century Dictionary and Cyclopedia" in p
    key = json.loads(CENTURY.data("scan_notation.json").read_text(encoding="utf-8"))
    for g in key["groups"]:
        for s in g["symbols"]:
            assert s["symbol"] in p, s
    # the mark that a model without the key misread: double dot under (ka̤l)
    assert "a̤" in p
