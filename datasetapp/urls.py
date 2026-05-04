from django.urls import path

from . import views

app_name = "datasetapp"
urlpatterns = [
    # Liveness probe for Docker HEALTHCHECK. Kept outside /admin/ so
    # Caddy/Cloudflare rate-limits don't apply to it.
    path("healthz", views.healthz, name="healthz"),
    # Home page
    path("", views.display_all, name="dataset-home-page"),
    # Get all details for a dataset
    path(
        "info/<slug:dataset_name>", views.about_dataset, name="dataset-about-a-dataset"
    ),
    # User initiated via the URL (not expected to be used): using a "GET" query
    path("file/<file_name>", views.download_dataset, name="dataset-download"),
    # Tags
    path("tag/<slug:tag>", views.display_by_tag, name="dataset-by-tag"),
]
