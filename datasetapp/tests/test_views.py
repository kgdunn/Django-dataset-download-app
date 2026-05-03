"""
Smoke tests for the four views in datasetapp.

These tests use SQLite (matching DJANGO_DEBUG=1 in dev), and exercise URL
resolution + the happy path of each view, plus the unknown-slug redirect.
They deliberately do NOT assert page content beyond status codes — the goal
is a CI tripwire for accidental view-level breakage, not template coverage.
"""

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
    response = client.get(
        reverse("datasetapp:dataset-download", args=["iris.csv"]),
        HTTP_USER_AGENT="pytest",
    )
    assert response.status_code == 302
    assert Hit.objects.count() == before + 1
