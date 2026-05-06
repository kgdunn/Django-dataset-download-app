"""
:copyright: Copyright 2010, by Kevin Dunn
:license: BSD, see LICENSE file for details.

Future enhancements
-------------------
Return better 404's

"""

import csv
import datetime
import io
import itertools
import json
import logging
import re

# Django imports
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse as django_reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

# Model imports
from .models import DataFile, Dataset, Hit, Tag

log_file = logging.getLogger("datasetapp")

# Public download URLs are restricted to a slug + 3-letter extension, matching
# Dataset.slug (a SlugField) and DataFile.file_type (always 3 letters today:
# CSV / XLS / XML / MAT). Anything else returns 404 — earlier the view raised
# ValueError on a missing/extra dot, which surfaced as a 500 and noise in the
# logs.
_DOWNLOAD_FILENAME_RE = re.compile(r"^[a-z0-9-]+\.[a-z]{3}$")

# Homepage free-text search (issue #94). ``icontains`` keeps SQLite dev and
# Postgres prod in lock-step; the catalogue is small enough that a six-field
# OR-of-LIKEs is cheaper than the migration + dev/CI divergence Postgres FTS
# would impose.
_SEARCH_FIELDS = (
    "name",
    "description",
    "data_source",
    "author_name",
    "tags__name",
    "tags__description",
)
_SEARCH_MAX_LEN = 100
_SEARCH_MAX_TOKENS = 8


def _search_filter(query):
    """Build a ``Q`` that ANDs whitespace tokens, ORed across each text field."""
    q = Q()
    for token in query.split()[:_SEARCH_MAX_TOKENS]:
        per_token = Q()
        for field in _SEARCH_FIELDS:
            per_token |= Q(**{f"{field}__icontains": token})
        q &= per_token
    return q


@never_cache
def healthz(request):
    # Liveness probe for Docker HEALTHCHECK and any upstream
    # depends_on: condition: service_healthy. Must not touch the DB,
    # render a template, or be cacheable — Caddy/Cloudflare caching a
    # stale "ok" past a failure would defeat the check.
    return HttpResponse("ok\n", content_type="text/plain")


def _annotate_with_downloads(queryset):
    """Attach a ``num_downloads`` aggregate to each ``Dataset`` row.

    ``distinct=True`` is required because callers may have already joined
    the M2M ``tags`` relation (``display_by_tag``); without it the tag
    join would multiply the Hit count by the number of matching tags.
    """
    return queryset.annotate(
        num_downloads=Count("datafile__hit", distinct=True),
    )


def display_by_tag(request, tag):
    """
    Shows only the datasets with the given tag
    """
    log_file.debug("Tag view for tag=%s" % tag)
    dataset_list = _annotate_with_downloads(
        Dataset.objects.filter(tags__name__startswith=tag)
    )

    context = {
        "dataset_list": dataset_list,
        "show_home_page": True,
        "current_tag": tag,
        "current_tag_description": Tag.objects.get(name__exact=tag).description,
    }

    return TemplateResponse(request, "datasetapp/all_datasets.html", context)


def display_all(request):
    """
    Displays all datasets in a table form, with brief summaries. An optional
    ``?q=<terms>`` query string filters the list by substring across the
    dataset name, description, data source, author name, and tag name /
    description; whitespace splits the query into tokens that must all match.
    """
    raw = (request.GET.get("q") or "").strip()[:_SEARCH_MAX_LEN]
    qs = Dataset.objects.order_by("slug")
    if raw:
        # ``.distinct()`` collapses duplicate rows produced by the M2M tag
        # join; it must be applied before ``_annotate_with_downloads`` so
        # the ``Count(distinct=True)`` aggregate sees a deduped row set.
        qs = qs.filter(_search_filter(raw)).distinct()
    dataset_list = _annotate_with_downloads(qs)[:]
    context = {
        "dataset_list": dataset_list,
        "query": raw,
        "result_count": len(dataset_list) if raw else None,
    }
    return TemplateResponse(request, "datasetapp/all_datasets.html", context)


def _csv_preview(file_obj, max_rows=10, max_bytes=100 * 1024):
    """First ``max_rows`` data rows of a CSV ``DataFile`` (header + rows), or None.

    The CSV is parsed with the default ``csv.excel`` dialect — the previous
    ``csv.Sniffer().sniff(...)`` call was reachable from any visitor hitting
    the detail page and has known catastrophic-backtracking behaviour on
    adversarial CSV input, so a malicious upload could pin a worker.
    Deterministic dialect = no DoS; the trade-off is that semicolon /
    tab-separated files now render as a single-column preview, which is
    acceptable for a preview (the underlying download is unaffected).
    """
    if file_obj is None or file_obj.file_type.upper() != "CSV":
        return None
    cache_key = f"csv_preview:{file_obj.id}:{max_rows}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        with file_obj.link_to_file.open("rb") as fh:
            raw = fh.read(max_bytes)
        text = raw.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text), csv.excel)
        rows = list(itertools.islice(reader, max_rows + 1))
    except Exception as e:
        log_file.warning("CSV preview failed for DataFile %s: %s", file_obj.id, e)
        rows = None
    cache.set(cache_key, rows, 60 * 60)
    return rows


def _download_series(dataset, days=365):
    """List of ``[yyyy-mm-dd, count]`` pairs for the last ``days`` days, zero-filled.

    Cached for one hour per dataset: the table grows monotonically and the
    aggregation walks the whole window on every call. Cache invalidates
    naturally on the hour; a missed download won't appear in the sparkline
    until then, which is fine for a 365-day chart.
    """
    cache_key = f"download_series:{dataset.pk}:{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = timezone.now().date()
    start = today - datetime.timedelta(days=days - 1)
    counts = (
        Hit.objects.filter(dataset_hit__dataset=dataset, date_and_time__date__gte=start)
        .annotate(day=TruncDate("date_and_time"))
        .values("day")
        .annotate(n=Count("id"))
    )
    counts_by_day = {row["day"]: row["n"] for row in counts}
    series = [
        [
            (start + datetime.timedelta(days=i)).isoformat(),
            counts_by_day.get(start + datetime.timedelta(days=i), 0),
        ]
        for i in range(days)
    ]
    cache.set(cache_key, series, 60 * 60)
    return series


def about_dataset(request, dataset_name=None):
    """
    Displays more information about a dataset
    """
    # django-name='dataset-about-a-dataset'

    # "slug" is the unique key in the "Dataset" table
    ds = Dataset.objects.filter(slug=dataset_name.lower()).first()
    if ds is None:
        log_file.error("An invalid dataset was requested: %s", dataset_name.lower())
        return HttpResponseRedirect(django_reverse("datasetapp:dataset-home-page"))

    files = DataFile.objects.filter(dataset=ds)

    # Prev/next navigation: use the same slug ordering as the homepage table.
    ordered_slugs = list(
        Dataset.objects.order_by("slug").values_list("slug", flat=True)
    )
    idx = ordered_slugs.index(ds.slug)
    prev_slug = ordered_slugs[idx - 1] if idx > 0 else None
    next_slug = ordered_slugs[idx + 1] if idx < len(ordered_slugs) - 1 else None
    prev_dataset = Dataset.objects.get(slug=prev_slug) if prev_slug else None
    next_dataset = Dataset.objects.get(slug=next_slug) if next_slug else None

    # CSV preview (skip when dataset is hidden, defence in depth).
    csv_file = files.filter(file_type__iexact="CSV").first()
    preview_rows = _csv_preview(csv_file) if not ds.is_hidden else None

    # ``download_dataset`` parses its URL as ``{slug}.{ext}``.
    dfile = files[0]
    download_file_name = f"{ds.slug}.{dfile.file_type.lower()}"

    # Python quickstart (only when a CSV is available).
    quickstart_url = None
    if csv_file is not None and not ds.is_hidden:
        quickstart_url = request.build_absolute_uri(
            django_reverse(
                "datasetapp:dataset-download",
                kwargs={"file_name": f"{ds.slug}.csv"},
            )
        )

    context = {
        "ds": ds,
        "dfile": dfile,
        "download_file_name": download_file_name,
        "num_hits": Hit.objects.filter(dataset_hit=dfile).count(),
        "prev_dataset": prev_dataset,
        "next_dataset": next_dataset,
        "preview_rows": preview_rows,
        "quickstart_url": quickstart_url,
        "download_series_json": json.dumps(_download_series(ds)),
    }
    return TemplateResponse(request, "datasetapp/dataset_info.html", context)


def download_dataset(request, file_name=None):
    """
    Downloads a dataset.  Wrap through a view function so that we can increment
    the hit counter.

    We arrive by: http://localhost/file/cheddar-cheese.csv
    Django streams the file body directly via ``FileResponse``. The earlier
    implementation returned a 302 to ``/media/datasets/cheddar-cheese.csv``,
    which doubled the surface exposed to Cloudflare's Bot Fight Mode and
    caused 403s for ``urllib`` / ``pandas.read_csv`` clients (issue #86).
    """
    # django-name='dataset-download'
    file_name = (file_name or "").lower()

    # Reject anything that isn't slug+single-dot+3-letter extension up front,
    # so a stray dot (or no dot at all) returns 404 rather than crashing the
    # view with a ValueError that surfaces as a 500.
    if not _DOWNLOAD_FILENAME_RE.match(file_name):
        log_file.warning("Rejected malformed download filename: %r", file_name)
        return HttpResponse("File not found", status=404)

    base_name, extension = file_name.rsplit(".", 1)

    # Which ``dataset`` object did this come from.  The file_name is the same
    # as the ``dataset`` object's slug (also the primary key) field.
    # Once we have the dataset, we can narrow down the file type with the
    # extension.
    dataset_instance = Dataset.objects.filter(slug=base_name).first()
    if dataset_instance is None:
        log_file.warning(
            "File not found; user request = %s; base_name=%s" % (file_name, base_name)
        )
        return HttpResponse("File not found", status=404)

    try:
        file_obj = DataFile.objects.filter(
            dataset=dataset_instance, file_type=extension.upper()
        )[0]
    except IndexError:
        log_file.error(
            "Data set instance exists, but file type (%s) was not "
            "found: %s" % (extension.upper(), str(dataset_instance))
        )
        return HttpResponse("Not found", status=404)

    # Increment hit counter
    try:
        Hit(dataset_hit=file_obj).save()
    except Exception as e:
        log_file.error("Failed to create Hit object: {0}".format(e))

    log_file.info("Successfully downloaded file: %s" % file_name)

    # FileResponse takes ownership of the file handle and closes it when the
    # response finishes streaming, so no `with` block is needed.
    return FileResponse(
        file_obj.link_to_file.open("rb"),
        as_attachment=True,
        filename=file_name,
    )
