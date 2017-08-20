from .models import Tag, Hit, DataFile, Dataset
from django.contrib import admin

class DatasetAdmin(admin.ModelAdmin):
    list_per_page = 2000
    list_display = ('name', 'slug', 'author_name', 'is_hidden', 'usage_restrictions', 'data_source', )

class HitAdmin(admin.ModelAdmin):
    list_per_page = 2000
    list_display = ('UA_string', 'dataset_hit', 'date_and_time', 'IP_address', 'referrer',)
    list_filter = ('UA_string', 'IP_address', 'dataset_hit', )

class DataFileAdmin(admin.ModelAdmin):
    list_per_page = 2000
    list_display = ('file_type', 'link_to_file', 'dataset')

admin.site.register(Tag)
admin.site.register(Hit, HitAdmin)
admin.site.register(DataFile, DataFileAdmin)
admin.site.register(Dataset, DatasetAdmin)