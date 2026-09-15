import re
from html import unescape

import bleach
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

register = template.Library()


# Bleach allowlist for the small bit of inline HTML that admins type into
# Dataset.description and Dataset.data_source. Anything outside this list is
# stripped at render time, so an admin (or anyone who briefly gets admin
# access) cannot inject <script>, <iframe>, or event-handler attributes that
# would execute in a visitor's browser.
_ALLOWED_TAGS = frozenset(
    [
        "a",
        "b",
        "i",
        "em",
        "strong",
        "sub",
        "sup",
        "code",
        "br",
        "p",
        "span",
        "ul",
        "ol",
        "li",
        "dl",
        "dt",
        "dd",
        "img",
    ]
)
_ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "span": ["class"],
    # <img>: src/alt/title/width/height only. Event handlers (onerror,
    # onload, …) are dropped because they're not on this list, and bleach
    # filters src by _ALLOWED_PROTOCOLS so `javascript:` is rejected.
    "img": ["src", "alt", "title", "width", "height"],
}
_ALLOWED_PROTOCOLS = frozenset(["http", "https", "mailto"])


@register.filter(name="sanitise_markup")
def sanitise_markup(value):
    """Render admin-authored HTML safely.

    LaTeX in ``\\(...\\)`` is left untouched: bleach escapes the backslashes
    as text, MathJax then re-parses the rendered DOM and renders the math.
    Returns the empty string for ``None`` input.
    """
    if value is None:
        return ""
    cleaned = bleach.clean(
        str(value),
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    return mark_safe(cleaned)  # noqa: S308 — sanitised one line above


# Tags that introduce a line break when the browser renders them. Django's
# strip_tags() deletes tags without substituting anything, so "<li>a</li>
# <li>b</li>" flattens to "ab" — splitting on these first is what keeps the
# words apart. Inline tags (<b>, <a>, <sup>, …) are deliberately absent: they
# sit mid-sentence and are removed by strip_tags() without a separator.
_BLOCK_SPLIT_RE = re.compile(
    r"</?(?:p|div|br|hr|li|ul|ol|dl|dt|dd|table|thead|tbody|tr|td|th"
    r"|h[1-6]|blockquote|pre|section|article)\b[^>]*>",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")
# A fragment already ending in one of these reads fine followed by a space;
# anything else gets a semicolon so two list items don't run together.
_SENTENCE_ENDINGS = ".?!:;,"


def _flatten(markup):
    """Collapses block-level HTML into a single line of readable prose.

    Splits ``markup`` on block boundaries, strips any remaining inline tags
    from each fragment, and rejoins the non-empty fragments, inserting ``;``
    where the preceding fragment does not already end in punctuation. HTML
    entities are unescaped so the template's autoescaping renders ``&amp;``
    as ``&`` rather than double-escaping it to a literal ``&amp;``.

    :param str markup: admin-authored HTML, e.g. ``Dataset.description``.
    :returns: one whitespace-normalised line of plain text.
    :rtype: str
    """
    fragments = []
    for chunk in _BLOCK_SPLIT_RE.split(markup):
        text = unescape(strip_tags(chunk)).strip()
        if not text:
            continue
        if fragments and fragments[-1][-1] not in _SENTENCE_ENDINGS:
            fragments[-1] += ";"
        fragments.append(text)
    return _WHITESPACE_RE.sub(" ", " ".join(fragments)).strip()


@register.filter(name="summarise")
def summarise(value, words=40):
    """Render admin-authored HTML as a short plain-text teaser.

    For list pages, where the full description is neither wanted nor
    renderable inside a table cell. The detail page keeps the real markup via
    ``sanitise_markup``; this filter is its flattened, truncated counterpart.

    The return value is a plain ``str``, *not* ``mark_safe``: every tag has
    been removed, so Django's autoescaping is exactly what should happen to
    what is left.

    :param value: the markup to summarise; ``None`` returns ``""``.
    :param words: word budget before an ellipsis is appended.
    :type words: int or str
    :rtype: str

    Example::

        {{ dataset.description|summarise:40 }}
    """
    if not value:
        return ""
    return Truncator(_flatten(str(value))).words(int(words), truncate=" \u2026")


@stringfilter
def slice_string(value, args):
    """
    Slices a string: returns characters in string, starting with ``start``
    and ending *one character* before ``end`` (i.e. Python slice semantics,
    ``value[start:end]``).

    When ``args`` is ``None`` (i.e. the filter is called without an
    argument) the function returns ``False`` and performs no slicing.

    Examples:
    {{ 'my_long_string' | slice_string:"2" }}   will return '_'
    {{ 'my_long_string' | slice_string:":2" }}  will return 'my'
    {{ 'my_long_string' | slice_string:"0:3" }} will return 'my_'
    {{ 'my_long_string' | slice_string:"3:7" }} will return 'long'
    {{ 'my_long_string' | slice_string:"8:" }}    will return 'string'
    {{ 'my_long_string' | slice_string:"8:100" }} will return 'string'
    {{ 'my_long_string' | slice_string:"8:14" }}  will return 'string'
    """
    sep = ":"
    if args is None:
        return False
    if ":" not in args:
        return value[int(args)]

    slicer = [int(arg.strip()) for arg in args.split(sep) if arg != ""]
    if args[0] == sep:
        start, end = 0, slicer[0]
    elif args[-1] == sep:
        start, end = slicer[0], len(value)
    else:
        start, end = slicer
    return value[start:end]


# slice_string.is_safe = True: rather leave off; incase use removes part of string
# that causes it to become unsafe.

register.filter("slice_string", slice_string)
