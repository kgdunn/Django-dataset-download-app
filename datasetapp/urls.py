from .views import display_all, display_by_tag, download_dataset, about_dataset
from django.conf.urls import url

urlpatterns = [

    # Home page
    #url(r'^$', list_detail.object_list, all_datasets, name='dataset-home-page'),
    url(r'^$', display_all, name='dataset-home-page'),

    # Get all details for a dataset
    url(r'^info/(?P<dataset_name>.*?)$', about_dataset, name='dataset-about-a-dataset'),

    # User initiated via the URL (not expected to be used): using a "GET" query
    url(r'^file/(?P<file_name>.*?)$', download_dataset, name='dataset-download'),

    # Tags
    url(r'^tag/(?P<tag>.*?)$', display_by_tag, name='dataset-by-tag'),
]
