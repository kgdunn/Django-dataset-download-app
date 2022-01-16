from django.urls import path
from . import views

app_name = "datasetapp"
urlpatterns = [
    # Home page
    path("", views.display_all, name="dataset-home-page"),
    # Get all details for a dataset
    path("info/<slug:dataset_name>", views.about_dataset, name="dataset-about-a-dataset"),
    # User initiated via the URL (not expected to be used): using a "GET" query
    path("file/<file_name>", views.download_dataset, name="dataset-download"),
    # Tags
    path("tag/<slug:tag>", views.display_by_tag, name="dataset-by-tag"),
]
