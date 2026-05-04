from django.contrib import admin

from .models import DataFile, Dataset, Hit, Tag


class DatasetAdmin(admin.ModelAdmin):
    list_per_page = 100
    list_display = (
        "name",
        "slug",
        "author_name",
        "is_hidden",
        "usage_restrictions",
        "data_source",
    )


class HitAdmin(admin.ModelAdmin):
    # `Hit` is an append-only audit log: rows are written by the public
    # download view and read by the per-dataset counter / sparkline. Editing
    # a row in admin would silently corrupt both. Lock both fields readonly
    # so the only mutation is row creation by the app itself.
    list_per_page = 100
    list_display = ("dataset_hit", "date_and_time")
    list_filter = ("date_and_time", "dataset_hit__dataset")
    date_hierarchy = "date_and_time"
    readonly_fields = ("dataset_hit", "date_and_time")


class DataFileAdmin(admin.ModelAdmin):
    list_per_page = 100
    list_display = ("file_type", "link_to_file", "dataset")


admin.site.register(Tag)
admin.site.register(Hit, HitAdmin)
admin.site.register(DataFile, DataFileAdmin)
admin.site.register(Dataset, DatasetAdmin)
