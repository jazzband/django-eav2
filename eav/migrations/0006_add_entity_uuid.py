from django.db import migrations, models


class Migration(migrations.Migration):
    """Creates UUID field to map to Entity FK."""

    dependencies = [
        ('eav', '0005_auto_20210510_1305'),
    ]

    operations = [
        migrations.AddField(
            model_name='value',
            name='entity_uuid',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='value',
            name='entity_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
