"""Tests for the ``summarise`` filter in ``datasetapp/templatetags/extra_tags.py``.

The homepage and ``/tag/<slug>`` list previously rendered descriptions with
``|striptags``. Django's ``strip_tags`` removes tags without substituting
whitespace, so an admin's ``<li>`` list arrived on the page as one fused word
("...temperaturesvariables 6 and 7..."). These tests pin the replacement.
"""

import pytest
from django.template import Context, Template

from datasetapp.templatetags.extra_tags import summarise

LIST_MARKUP = (
    "<p>Variables 1, 2, 3: reactor temperatures</p>"
    "<ul><li>variables 6 and 7 are heating media</li>"
    "<li>variables 4, 8, and 9 are pressures</li></ul>"
)


def test_block_boundaries_do_not_fuse_words():
    out = summarise(LIST_MARKUP)
    assert "temperaturesvariables" not in out
    assert "mediavariables" not in out
    assert out.startswith("Variables 1, 2, 3: reactor temperatures; variables 6")


def test_fragments_without_punctuation_get_a_separator():
    # "media" ends no sentence, so the next fragment needs one.
    assert "heating media; variables 4" in summarise(LIST_MARKUP)


def test_fragment_ending_in_punctuation_keeps_its_own():
    out = summarise("<p>One sentence.</p><p>Another one.</p>")
    assert out == "One sentence. Another one."


def test_inline_tags_are_removed_without_a_separator():
    assert summarise("<p>A <b>bold</b> claim</p>") == "A bold claim"


def test_entities_are_unescaped_once():
    # striptags left "&amp;" alone, so autoescaping turned it into a literal
    # "&amp;" on the page.
    assert summarise("<p>Fisher &amp; Sons</p>") == "Fisher & Sons"


def test_whitespace_is_collapsed():
    assert summarise("<p>two\n\n   lines</p>") == "two lines"


def test_truncates_to_the_word_budget():
    out = summarise("<p>" + " ".join(str(i) for i in range(50)) + "</p>", 10)
    assert out == "0 1 2 3 4 5 6 7 8 9 …"


def test_word_budget_accepts_a_template_string_argument():
    assert summarise("<p>one two three</p>", "2") == "one two …"


@pytest.mark.parametrize("value", [None, "", "   ", "<p></p>"])
def test_empty_input_renders_nothing(value):
    assert summarise(value) == ""


def test_output_is_escaped_by_the_template():
    """The filter returns a plain str, so autoescaping still applies.

    An admin who typed the *entity* ``&lt;script&gt;`` gets it unescaped to
    text by the filter; Django must escape it again on the way out.
    """
    rendered = Template("{% load extra_tags %}{{ d|summarise }}").render(
        Context({"d": "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"})
    )
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
