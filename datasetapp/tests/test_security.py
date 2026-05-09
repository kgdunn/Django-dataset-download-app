"""Security-regression tests for v1.5.0 hardening (see docs/SECURITY.md).

Each test pins a specific finding so that future refactors can't quietly
re-open the hole.
"""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse

from datasetapp.models import DataFile, Dataset, Hit
from datasetapp.templatetags.extra_tags import sanitise_markup

# Cache-clearing fixture is autouse-loaded from datasetapp/tests/conftest.py.


# ---------------------------------------------------------------- sanitiser --


@pytest.mark.parametrize(
    "raw,banned",
    [
        ("<script>alert(1)</script>", "<script"),
        ("<iframe src='evil'></iframe>", "<iframe"),
        ("<img src=x onerror=alert(1)>", "onerror"),
        ('<a href="javascript:alert(1)">x</a>', "javascript:"),
        ("<svg onload=alert(1)>", "onload"),
        ("<style>body{background:url(javascript:alert(1))}</style>", "<style"),
    ],
)
def test_sanitise_markup_strips_dangerous_constructs(raw, banned):
    cleaned = sanitise_markup(raw)
    assert banned not in cleaned


@pytest.mark.parametrize(
    "raw,kept",
    [
        ("<b>bold</b>", "<b>bold</b>"),
        ("<i>italic</i>", "<i>italic</i>"),
        ("<sub>2</sub>", "<sub>2</sub>"),
        ("<sup>3</sup>", "<sup>3</sup>"),
        (
            '<a href="https://example.org/x">link</a>',
            '<a href="https://example.org/x">link</a>',
        ),
        (
            '<img src="/media/datasets/foo.png" alt="caption">',
            'src="/media/datasets/foo.png"',
        ),
    ],
)
def test_sanitise_markup_preserves_allowed_tags(raw, kept):
    assert kept in sanitise_markup(raw)


def test_sanitise_markup_strips_event_handlers_from_img():
    """`<img>` is on the allowlist (so admins can embed dataset figures),
    but its event-handler attributes are not — `onerror` / `onload` must be
    dropped, and `javascript:` `src` values must be rejected by the protocol
    allowlist."""
    cleaned = sanitise_markup(
        '<img src="/media/x.png" onerror="alert(1)" onload="alert(2)">'
    )
    assert "<img" in cleaned
    assert 'src="/media/x.png"' in cleaned
    assert "onerror" not in cleaned
    assert "onload" not in cleaned

    cleaned_js = sanitise_markup('<img src="javascript:alert(1)">')
    assert "javascript:" not in cleaned_js


def test_sanitise_markup_keeps_latex_intact():
    """MathJax operates on text-content, so escaped backslashes and dollar
    signs round-trip through bleach unchanged."""
    raw = r"Cheese moisture is \(m = \rho V\) and pH is $pH$."
    cleaned = sanitise_markup(raw)
    assert r"\(m = \rho V\)" in cleaned
    assert "$pH$" in cleaned


def test_sanitise_markup_handles_none_and_empty():
    assert sanitise_markup(None) == ""
    assert sanitise_markup("") == ""


# --------------------------------------------------- detail page rendering --


def test_detail_page_does_not_render_admin_supplied_script(client, db):
    ds = Dataset.objects.create(
        name="Iris",
        slug="iris-xss",
        description=(
            '<script>alert("xss-1")</script>'
            '<img src=x onerror=alert("xss-2")>'
            "<b>safe-bold</b>"
        ),
        author_name="A",
        usage_restrictions="None",
        data_source='<iframe src="evil"></iframe><a href="javascript:alert(1)">x</a>',
    )
    DataFile.objects.create(
        file_type="CSV", link_to_file="datasets/iris-xss.csv", dataset=ds
    )
    response = client.get(reverse("datasetapp:dataset-about-a-dataset", args=[ds.slug]))
    body = response.content.decode()
    assert response.status_code == 200
    # The page-supplied <script> tags include the ECharts setup block;
    # what matters is that no admin-injected executable construct survives.
    # bleach drops disallowed tag wrappers entirely (strip=True) and strips
    # disallowed attributes from allowed tags. <img> is on the allowlist
    # (v1.6.3) so its wrapper survives, but its event-handler attributes
    # (onerror, onload) must not.
    description_block = body.split("<dt>Description</dt>")[1].split("</dd>")[0]
    data_source_block = body.split("<dt>Data source</dt>")[1].split("</dd>")[0]
    for block in (description_block, data_source_block):
        assert "<script" not in block.lower()
        assert "<iframe" not in block.lower()
        assert "onerror" not in block.lower()
        assert "onload" not in block.lower()
        assert "javascript:" not in block.lower()
    # The allowed <b> tag must survive intact.
    assert "<b>safe-bold</b>" in description_block


# ---------------------------------------------------- download_dataset 404 --


@pytest.mark.parametrize(
    "bad_name",
    [
        "noextension",  # no dot
        "two.dots.csv",  # multiple dots
        "name.toolongext",  # extension > 3 letters
        ".csv",  # empty base
        "iris.cs",  # extension < 3 letters
        "iris.CSV",  # uppercase rejected pre-lowercase (still passes regex after .lower())
    ],
)
def test_download_dataset_returns_404_not_500_for_bad_filenames(client, db, bad_name):
    """Pre-v1.5.0 these raised ValueError on `[a, b] = name.split('.')`,
    surfacing as 500s. Now they all 404."""
    response = client.get(reverse("datasetapp:dataset-download", args=[bad_name]))
    assert response.status_code == 404


def test_download_dataset_unknown_slug_returns_404(client, db):
    response = client.get(
        reverse("datasetapp:dataset-download", args=["does-not-exist.csv"])
    )
    assert response.status_code == 404


def test_download_dataset_no_hit_row_on_bad_filename(client, db):
    before = Hit.objects.count()
    client.get(reverse("datasetapp:dataset-download", args=["nope"]))
    assert Hit.objects.count() == before


# -------------------------------------------------------- DataFile.clean() --


def test_datafile_clean_rejects_extension_mismatch(db):
    ds = Dataset.objects.create(
        name="X",
        slug="ext-mismatch",
        description="d",
        author_name="a",
        usage_restrictions="None",
        data_source="s",
    )
    df = DataFile(
        file_type="CSV",
        link_to_file="datasets/ext-mismatch.xls",
        dataset=ds,
    )
    with pytest.raises(ValidationError):
        df.full_clean()


def test_datafile_clean_accepts_xlsx_for_xls_filetype(db):
    ds = Dataset.objects.create(
        name="X",
        slug="xlsx-ok",
        description="d",
        author_name="a",
        usage_restrictions="None",
        data_source="s",
    )
    df = DataFile(
        file_type="XLS",
        link_to_file="datasets/xlsx-ok.xlsx",
        dataset=ds,
    )
    df.full_clean()  # should not raise


# ---------------------------------------------------- csv preview safety --


def test_csv_preview_returns_none_on_unreadable_file(db):
    """The view must swallow errors from a missing/corrupt CSV and return
    None so the template falls back to "no preview" rather than 500-ing."""
    from datasetapp.views import _csv_preview

    ds = Dataset.objects.create(
        name="X",
        slug="bad-csv",
        description="d",
        author_name="a",
        usage_restrictions="None",
        data_source="s",
    )
    df = DataFile.objects.create(
        file_type="CSV", link_to_file="datasets/does-not-exist.csv", dataset=ds
    )
    # File has never been written to disk; .open() will raise.
    assert _csv_preview(df) is None


# --------------------------------------------- security headers middleware --


def test_security_headers_present_on_homepage(client, db):
    response = client.get(reverse("datasetapp:dataset-home-page"))
    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert "interest-cohort=()" in response.headers.get("Permissions-Policy", "")


# ------------------------------------------- _download_series cache hit --


def test_download_series_uses_cache(client, db):
    """Verify the cache layer added in v1.5.0 — second call avoids the DB."""
    from datasetapp.views import _download_series

    ds = Dataset.objects.create(
        name="X",
        slug="cache-check",
        description="d",
        author_name="a",
        usage_restrictions="None",
        data_source="s",
    )
    df = DataFile.objects.create(
        file_type="CSV", link_to_file="datasets/cache-check.csv", dataset=ds
    )
    Hit.objects.create(dataset_hit=df)
    first = _download_series(ds)
    # If we add another Hit but the cache is warm, the series shouldn't change.
    Hit.objects.create(dataset_hit=df)
    second = _download_series(ds)
    assert first == second
    # After clearing the cache the new Hit should appear. Two hits in the
    # current week amount to ``2 / 7`` once the daily-average aggregation
    # kicks in (issue #104).
    cache.clear()
    third = _download_series(ds)
    assert sum(point[1] for point in third) == pytest.approx(2 / 7, abs=1e-4)


# ------------------------------------- special_message no longer in context --


def test_homepage_no_longer_carries_special_message_context(client, db):
    """Defence: if a future commit re-introduces the variable, the |safe
    template chain is gone, so the worst case is plain-text rendering."""
    from datasetapp import views

    with patch.object(views, "TemplateResponse", wraps=views.TemplateResponse) as spy:
        client.get(reverse("datasetapp:dataset-home-page"))
        # Inspect the context dict passed to TemplateResponse.
        ctx = spy.call_args.args[2]
        assert "special_message" not in ctx
