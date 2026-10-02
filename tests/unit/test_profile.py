"""The Century's profile: the facts this book tells the engine."""
import pytest

from century import CENTURY, IA_ITEMS
from wikikit.corpora import current_corpus


def test_the_committed_book_is_the_century():
    assert current_corpus() is CENTURY


def test_every_volume_has_a_scan_and_a_page_count():
    assert sorted(IA_ITEMS) == CENTURY.volumes == list(range(1, 11))
    assert CENTURY.scan_name(10) == "willcenturydicti10whit"


def test_the_century_refuses_a_volume_it_does_not_have():
    with pytest.raises(ValueError, match="volumes 1-10"):
        CENTURY.scan_name(11)
