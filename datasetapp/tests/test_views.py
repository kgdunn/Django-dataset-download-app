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


@pytest.fixture
def csv_file(db, dataset):
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


def test_download_known_file_returns_302_and_increments_hits(client, dataset, csv_file):
    before = Hit.objects.count()
    response = client.get(reverse("datasetapp:dataset-download", args=["iris.csv"]))
    assert response.status_code == 302
    assert Hit.objects.count() == before + 1


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
    assert len(series) == 365
    assert all(len(point) == 2 for point in series)
    assert sum(point[1] for point in series) == 1
