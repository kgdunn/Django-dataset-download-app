"""
    :copyright: Copyright 2010, by Kevin Dunn
    :license: BSD, see LICENSE file for details.
"""
from django.db import models


class Tag(models.Model):
    """
    A tag object: each dataset can be tagged.  All tags must have a unique name.
    """

    name = models.SlugField(unique=True)
    description = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DatasetManager(models.Manager):
    def get_query_set(self):
        return super(DatasetManager, self).get_query_set().filter(is_hidden=False)


class Dataset(models.Model):
    """Defines a dataset instance.

    Note: each ``Dataset`` instance can have multiple file formats, ``DataFile``
          instances, but each ``DataFile`` can point back only to one dataset.
          So it is a one-to-many relationship using ForeignKey()
    """

    objects = DatasetManager()
    usage_choice = (
        ("None", "None  "),
        ("Unknown", "Unknown"),
        ("Not-commercial", "May not be used for commercial purposes"),
    )

    # The dataset's displayed name
    name = models.CharField(max_length=500)
    slug = models.SlugField(unique=True)

    # Long description of the data set
    description = models.TextField()

    # Who's responsible for the dataset?
    author_name = models.CharField(max_length=250)
    author_email = models.EmailField(blank=True)
    author_URL = models.URLField(max_length=500, blank=True)

    # Display it on website?
    is_hidden = models.BooleanField(default=False)

    # Show preview on the website?
    show_full_preview = models.BooleanField(default=False)

    # Usage restrictions. e.g no commercial use, no restrictions, etc
    usage_restrictions = models.CharField(choices=usage_choice, max_length=250)

    # Description about where this data came from
    data_source = models.TextField()

    # More information about the data (private: never displayed on website)
    more_info_source = models.TextField(blank=True)

    # Rows and columns of *data* (ignoring column labels)
    rows = models.PositiveIntegerField(blank=True, null=True)
    cols = models.PositiveIntegerField(blank=True, null=True)

    # Created on, Updated on
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(
        Tag,
        blank=True,
    )

    def __str__(self):
        return f"Dataset slug: {self.slug}"

    class Meta:
        ordering = ["slug"]


class DataFile(models.Model):
    """
    Defines a link to a data file in a particular format e.g XLS, CSV, MAT.

    Note: each data file can only correspond to one ``Dataset`` instance. It's
          like the ``Book`` in the limited Book-Authors case, where each book
          can only have one author, but each author (Dataset) can have multiple
          books (``DataFile``).

    The dataset to which a ``DataFile`` object points: datafile.dataset_set.all()[0]

    Note: file data file must obey the following rules:

        1. The file_name must be the same as the ``Dataset`` slug field
        2. The extension must be one of the entries in ``file_type_choice``

    """

    # Short name (usually 3 characters) and description on how to use it
    file_type_choice = (
        ("CSV", "Comma Separated Value file"),
        ("XLS", "Microsoft Excel"),
        ("XML", "eXtensible Markup Language"),
        ("MAT", "MATLAB MAT file"),
    )

    file_type = models.CharField(choices=file_type_choice, max_length=50)
    link_to_file = models.FileField(upload_to="datasets/", max_length=500)
    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.file_type}  :  {self.link_to_file}"


class Hit(models.Model):
    """
    Tracks dataset hits to a *download* of the dataset (not just to view it)
    """

    UA_string = models.CharField(max_length=500)  # user agent of browser
    IP_address = models.GenericIPAddressField()
    date_and_time = models.DateTimeField(auto_now=True)
    dataset_hit = models.ForeignKey(DataFile, on_delete=models.PROTECT)
    referrer = models.TextField(max_length=500)

    def __str__(self):
        return (
            f"{str(self.date_and_time)[0:19]}: from IP={self.IP_address} visited "
            f"<<{self.dataset_hit}>> [refer: {self.referrer}]"
        )
