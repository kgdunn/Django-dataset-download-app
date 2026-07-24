"""
    :copyright: Copyright 2010, by Kevin Dunn
    :license: BSD, see LICENSE file for details.
"""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
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
    def get_queryset(self):
        return super().get_queryset().filter(is_hidden=False)


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
    Defines a link to a data file in a particular format e.g XLSX, CSV, MAT.

    Note: each data file can only correspond to one ``Dataset`` instance. It's
          like the ``Book`` in the limited Book-Authors case, where each book
          can only have one author, but each author (Dataset) can have multiple
          books (``DataFile``).

    The dataset to which a ``DataFile`` object points: datafile.dataset

    Note: file data file must obey the following rules:

        1. The file_name must be the same as the ``Dataset`` slug field
        2. The extension must be one of the entries in ``file_type_choice``

    """

    # Short name (usually 3 characters) and description on how to use it
    file_type_choice = (
        ("CSV", "Comma Separated Value file"),
        ("XLSX", "Microsoft Excel"),
        ("XML", "eXtensible Markup Language"),
        ("MAT", "MATLAB MAT file"),
    )

    file_type = models.CharField(choices=file_type_choice, max_length=50)
    link_to_file = models.FileField(
        upload_to="datasets/",
        max_length=500,
        # Reject anything that isn't one of the four data formats we serve.
        # Stops an admin (or a phished admin session) from uploading e.g. an
        # `.html` file that Caddy would happily serve as text/html.
        validators=[
            FileExtensionValidator(
                allowed_extensions=["csv", "xls", "xlsx", "xml", "mat"]
            )
        ],
    )
    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT)

    def clean(self):
        """Reject mismatches between the declared ``file_type`` and the
        actual file extension. ``download_dataset`` resolves URLs by
        ``(slug, file_type.upper())``; if the two disagree, a `.csv`
        request can silently serve `.xls` bytes and vice versa.
        """
        super().clean()
        if not self.link_to_file or not self.file_type:
            return
        actual_ext = Path(self.link_to_file.name).suffix.lower().lstrip(".")
        # Treat the legacy .xls extension as valid for the XLSX file_type, so
        # datasets uploaded before issue #113 don't fail validation on re-save.
        valid_ext = {"xlsx": {"xls", "xlsx"}}.get(
            self.file_type.lower(), {self.file_type.lower()}
        )
        if actual_ext not in valid_ext:
            raise ValidationError(
                {
                    "link_to_file": (
                        f"File extension '.{actual_ext}' does not match "
                        f"the declared file type '{self.file_type}'."
                    )
                }
            )

    def __str__(self):
        return f"{self.file_type}  :  {self.link_to_file}"


class Hit(models.Model):
    """
    One row per dataset download. Stores only the file reference and the
    timestamp — no IP, User-Agent, or referrer — so the table can be retained
    indefinitely without holding visitor PII (see #17).
    """

    date_and_time = models.DateTimeField(auto_now=True)
    dataset_hit = models.ForeignKey(DataFile, on_delete=models.PROTECT)

    def __str__(self):
        return f"{str(self.date_and_time)[0:19]}: <<{self.dataset_hit}>>"
