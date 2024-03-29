# Generated by Django 3.2.11 on 2022-01-15 23:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_type', models.CharField(choices=[('CSV', 'Comma Separated Value file'), ('XLS', 'Microsoft Excel'), ('XML', 'eXtensible Markup Language'), ('MAT', 'MATLAB MAT file')], max_length=50)),
                ('link_to_file', models.FileField(max_length=500, upload_to='datasets/')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.SlugField(unique=True)),
                ('description', models.CharField(max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name='Hit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('UA_string', models.CharField(max_length=500)),
                ('IP_address', models.GenericIPAddressField()),
                ('date_and_time', models.DateTimeField(auto_now=True)),
                ('referrer', models.TextField(max_length=500)),
                ('dataset_hit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='datasetapp.datafile')),
            ],
        ),
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField()),
                ('author_name', models.CharField(max_length=250)),
                ('author_email', models.EmailField(blank=True, max_length=254)),
                ('author_URL', models.URLField(blank=True, max_length=500)),
                ('is_hidden', models.BooleanField(default=False)),
                ('show_full_preview', models.BooleanField(default=False)),
                ('usage_restrictions', models.CharField(choices=[('None', 'None  '), ('Unknown', 'Unknown'), ('Not-commercial', 'May not be used for commercial purposes')], max_length=250)),
                ('data_source', models.TextField()),
                ('more_info_source', models.TextField(blank=True)),
                ('rows', models.PositiveIntegerField(blank=True, null=True)),
                ('cols', models.PositiveIntegerField(blank=True, null=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('tags', models.ManyToManyField(blank=True, to='datasetapp.Tag')),
            ],
            options={
                'ordering': ['slug'],
            },
        ),
        migrations.AddField(
            model_name='datafile',
            name='dataset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='datasetapp.dataset'),
        ),
    ]
