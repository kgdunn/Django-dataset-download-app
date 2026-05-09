"""
Smoke tests for the four views in datasetapp.

These tests use SQLite (matching DJANGO_DEBUG=1 in dev), and exercise URL
resolution + the happy path of each view, plus the unknown-slug redirect.
They deliberately do NOT assert page content beyond status codes — the goal
is a CI tripwire for accidental view-level breakage, not template coverage.
"""

import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from datasetapp.models import DataFile, Dataset, Hit, Tag


@pytest.fixture
def dataset(db):
    return Dataset.objects.create(
        name="Iris",
        slug="iris",
        description="Iris flowers dataset.",
        author_name="R. A. Fisher",
        usage_restrictions="None",
        data_source="Original publication, 1936.",
    )


CSV_FIXTURE_BYTES = b"sepal,petal\n5.1,1.4\n4.9,1.4\n"


@pytest.fixture
def csv_file(db, dataset, settings, tmp_path):
    # download_dataset now streams the file via FileResponse, so the bytes
    # must actually exist on disk under MEDIA_ROOT.
    settings.MEDIA_ROOT = tmp_path
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    (datasets_dir / "iris.csv").write_bytes(CSV_FIXTURE_BYTES)
    return DataFile.objects.create(
        file_type="CSV",
        link_to_file="datasets/iris.csv",
        dataset=dataset,
    )


@pytest.fixture
def tag(db, dataset):
    t = Tag.objects.create(name="chemistry", description="Chemistry datasets")
    dataset.tags.add(t)
    return t


def test_home_returns_200(client, dataset):
    response = client.get(reverse("datasetapp:dataset-home-page"))
    assert response.status_code == 200


def test_home_renders_downloads_column_with_per_dataset_counts(
    client, dataset, csv_file
):
    Hit.objects.create(dataset_hit=csv_file)
    Hit.objects.create(dataset_hit=csv_file)
    response = client.get(reverse("datasetapp:dataset-home-page"))
    body = response.content.decode()
    assert response.status_code == 200
    assert 'data-sort-key="downloads"' in body
    assert 'class="dataset-downloads"' in body
    assert 'data-sort-value="2"' in body


def test_tag_view_does_not_double_count_downloads(client, db):
    ds = Dataset.objects.create(
        name="Multi",
        slug="multi",
        description="d",
        author_name="a",
        usage_restrictions="None",
        data_source="s",
    )
    df = DataFile.objects.create(
        file_type="CSV", link_to_file="datasets/multi.csv", dataset=ds
    )
    # Two tags both starting with "chem" would otherwise multiply the Hit
    # count via the M2M join in display_by_tag.
    for tag_name in ("chem", "chemistry"):
        t = Tag.objects.create(name=tag_name, description="x")
        ds.tags.add(t)
    Hit.objects.create(dataset_hit=df)
    Hit.objects.create(dataset_hit=df)
    Hit.objects.create(dataset_hit=df)

    response = client.get(reverse("datasetapp:dataset-by-tag", args=["chem"]))
    body = response.content.decode()
    assert response.status_code == 200
    assert 'data-sort-value="3"' in body
    assert 'data-sort-value="6"' not in body


def _make_dataset(slug, name, description="d", data_source="s", author_name="a"):
    return Dataset.objects.create(
        name=name,
        slug=slug,
        description=description,
        author_name=author_name,
        usage_restrictions="None",
        data_source=data_source,
    )


def test_home_search_matches_substring_in_name(client, db):
    _make_dataset("iris", "Iris")
    _make_dataset("cheese", "Cheddar Cheese")
    response = client.get(reverse("datasetapp:dataset-home-page"), {"q": "iri"})
    body = response.content.decode()
    assert response.status_code == 200
    assert ">Iris</a>" in body
    assert ">Cheddar Cheese</a>" not in body
    assert "1 result for" in body


def test_home_search_matches_substring_in_description(client, db):
    _make_dataset("alpha", "Alpha", description="Contains XYZUNIQUE marker.")
    _make_dataset("beta", "Beta", description="Different content.")
    response = client.get(reverse("datasetapp:dataset-home-page"), {"q": "xyzunique"})
    body = response.content.decode()
    assert response.status_code == 200
    assert ">Alpha</a>" in body
    assert ">Beta</a>" not in body


def test_home_search_matches_via_tag_name(client, db):
    tagged = _make_dataset("tagged", "Tagged")
    untagged = _make_dataset("untagged", "Untagged")  # noqa: F841
    t = Tag.objects.create(name="chemistry", description="Chemistry datasets")
    tagged.tags.add(t)
    response = client.get(reverse("datasetapp:dataset-home-page"), {"q": "chem"})
    body = response.content.decode()
    assert response.status_code == 200
    assert ">Tagged</a>" in body
    assert ">Untagged</a>" not in body


def test_home_search_no_results_renders_empty_state(client, db):
    _make_dataset("iris", "Iris")
    response = client.get(
        reverse("datasetapp:dataset-home-page"), {"q": "zzznotfoundzzz"}
    )
    body = response.content.decode()
    assert response.status_code == 200
    assert "No datasets matched" in body
    assert "0 results for" in body


def test_home_search_does_not_double_count_via_tag_join(client, db):
    ds = _make_dataset("multi", "Multi")
    for tag_name in ("chem", "chemistry"):
        t = Tag.objects.create(name=tag_name, description="x")
        ds.tags.add(t)
    response = client.get(reverse("datasetapp:dataset-home-page"), {"q": "chem"})
    body = response.content.decode()
    assert response.status_code == 200
    # Without `.distinct()` the M2M tag join would produce two rows.
    assert body.count('class="dataset-row"') == 1


def test_home_without_search_renders_intro_message(client, dataset):
    response = client.get(reverse("datasetapp:dataset-home-page"))
    body = response.content.decode()
    assert response.status_code == 200
    assert 'id="special_message"' in body
    assert "result for" not in body


def test_about_known_slug_returns_200(client, dataset, csv_file):
    response = client.get(
        reverse("datasetapp:dataset-about-a-dataset", args=[dataset.slug])
    )
    assert response.status_code == 200


def test_about_unknown_slug_redirects_home(client, db):
    response = client.get(
        reverse("datasetapp:dataset-about-a-dataset", args=["does-not-exist"])
    )
    assert response.status_code == 302
    assert response.url == reverse("datasetapp:dataset-home-page")


def test_tag_view_returns_200(client, dataset, tag):
    response = client.get(reverse("datasetapp:dataset-by-tag", args=[tag.name]))
    assert response.status_code == 200


def test_download_known_file_streams_bytes_and_increments_hits(
    client, dataset, csv_file
):
    before = Hit.objects.count()
    response = client.get(reverse("datasetapp:dataset-download", args=["iris.csv"]))
    assert response.status_code == 200
    assert Hit.objects.count() == before + 1
    assert response["Content-Disposition"] == 'attachment; filename="iris.csv"'
    assert b"".join(response.streaming_content) == CSV_FIXTURE_BYTES


def test_download_malformed_filename_returns_404_without_hit(client, dataset, csv_file):
    before = Hit.objects.count()
    response = client.get(reverse("datasetapp:dataset-download", args=["NOT-A-SLUG"]))
    assert response.status_code == 404
    assert Hit.objects.count() == before


def test_about_includes_prev_next_when_neighbours_exist(client, db):
    for slug, name in [("a-set", "Alpha"), ("b-set", "Beta"), ("c-set", "Gamma")]:
        ds = Dataset.objects.create(
            name=name,
            slug=slug,
            description="d",
            author_name="a",
            usage_restrictions="None",
            data_source="s",
        )
        DataFile.objects.create(
            file_type="CSV", link_to_file=f"datasets/{slug}.csv", dataset=ds
        )

    response = client.get(reverse("datasetapp:dataset-about-a-dataset", args=["b-set"]))
    body = response.content.decode()
    assert response.status_code == 200
    assert "/info/a-set" in body
    assert "/info/c-set" in body

    # Boundary datasets only have one neighbour link.
    first = client.get(
        reverse("datasetapp:dataset-about-a-dataset", args=["a-set"])
    ).content.decode()
    assert "/info/b-set" in first
    assert "/info/c-set" not in first
    last = client.get(
        reverse("datasetapp:dataset-about-a-dataset", args=["c-set"])
    ).content.decode()
    assert "/info/b-set" in last
    assert "/info/a-set" not in last


def test_about_csv_preview_renders_when_csv_present(client, dataset, csv_file):
    fake_rows = [["sepal", "petal"], ["5.1", "1.4"], ["4.9", "1.4"]]
    with patch("datasetapp.views._csv_preview", return_value=fake_rows):
        response = client.get(
            reverse("datasetapp:dataset-about-a-dataset", args=[dataset.slug])
        )
    body = response.content.decode()
    assert response.status_code == 200
    assert "Preview (first 2 rows)" in body
    assert "sepal" in body and "petal" in body
    assert "5.1" in body and "4.9" in body


def test_about_omits_preview_when_only_non_csv_files(client, db):
    ds = Dataset.objects.create(
        name="X",
        slug="x",
        description="d",
        author_name="a",
        usage_restrictions="None",
        data_source="s",
    )
    DataFile.objects.create(file_type="MAT", link_to_file="datasets/x.mat", dataset=ds)
    response = client.get(reverse("datasetapp:dataset-about-a-dataset", args=["x"]))
    assert response.status_code == 200
    assert "dataset-preview" not in response.content.decode()


def test_healthz_returns_200_plain_ok(client, db):
    response = client.get(reverse("datasetapp:healthz"))
    assert response.status_code == 200
    assert response.content == b"ok\n"
    assert response.headers["Content-Type"].startswith("text/plain")


def test_healthz_disables_caching(client, db):
    # @never_cache must be applied so Caddy/Cloudflare can't serve a stale
    # "ok" past the point of failure.
    response = client.get(reverse("datasetapp:healthz"))
    cache_control = response.headers.get("Cache-Control", "")
    assert "no-cache" in cache_control
    assert "no-store" in cache_control
    assert "max-age=0" in cache_control


def test_healthz_does_not_record_a_hit(client, db):
    before = Hit.objects.count()
    client.get(reverse("datasetapp:healthz"))
    assert Hit.objects.count() == before


def test_about_includes_download_series_for_sparkline(client, dataset, csv_file):
    Hit.objects.create(dataset_hit=csv_file)
    response = client.get(
        reverse("datasetapp:dataset-about-a-dataset", args=[dataset.slug])
    )
    body = response.content.decode()
    assert response.status_code == 200
    assert "downloads-sparkline" in body
    # Pull the JSON literal out of the inline script and verify shape.
    marker = "var data = "
    start = body.index(marker) + len(marker)
    end = body.index(";", start)
    series = json.loads(body[start:end])
    # Seven years of weekly buckets (issue #104).
    assert len(series) == 7 * 52
    assert all(len(point) == 2 for point in series)
    # One hit landed in the most recent week and is reported as a weekly total.
    assert sum(point[1] for point in series) == 1
