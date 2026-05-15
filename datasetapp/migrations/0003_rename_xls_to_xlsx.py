from django.db import migrations, models


def xls_to_xlsx(apps, schema_editor):
    DataFile = apps.get_model("datasetapp", "DataFile")
    DataFile.objects.filter(file_type="XLS").update(file_type="XLSX")


def xlsx_to_xls(apps, schema_editor):
    DataFile = apps.get_model("datasetapp", "DataFile")
    DataFile.objects.filter(file_type="XLSX").update(file_type="XLS")


class Migration(migrations.Migration):

    dependencies = [
        ("datasetapp", "0002_drop_hit_pii"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datafile",
            name="file_type",
            field=models.CharField(
                choices=[
                    ("CSV", "Comma Separated Value file"),
                    ("XLSX", "Microsoft Excel"),
                    ("XML", "eXtensible Markup Language"),
                    ("MAT", "MATLAB MAT file"),
                ],
                max_length=50,
            ),
        ),
        migrations.RunPython(xls_to_xlsx, xlsx_to_xls),
    ]
