from django.contrib import admin

from .models import DataFile, Dataset, Hit, Tag


class DatasetAdmin(admin.ModelAdmin):
    list_per_page = 2000
    list_display = (
        "name",
        "slug",
        "author_name",
        "is_hidden",
        "usage_restrictions",
        "data_source",
    )


class HitAdmin(admin.ModelAdmin):
    list_per_page = 2000
    list_display = (
        "dataset_hit",
        "date_and_time",
    )
    list_filter = ("dataset_hit",)


class DataFileAdmin(admin.ModelAdmin):
    list_per_page = 2000
    list_display = ("file_type", "link_to_file", "dataset")


admin.site.register(Tag)
admin.site.register(Hit, HitAdmin)
admin.site.register(DataFile, DataFileAdmin)
admin.site.register(Dataset, DatasetAdmin)
