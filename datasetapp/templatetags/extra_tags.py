import bleach
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

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


@stringfilter
def slice_string(value, args):
    """
    Slices a string: returns characters in string, starting with ``start``
    and ending *one character* before ``end`` (i.e. Python slice semantics,
    ``value[start:end]``).

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
