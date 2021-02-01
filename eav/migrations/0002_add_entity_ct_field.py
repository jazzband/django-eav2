from django.db import migrations, models


class Migration(migrations.Migration):
    """Add entity_ct field to Attribute model."""

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('eav', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='entity_ct',
            field=models.ManyToManyField(blank=True, to='contenttypes.ContentType'),
        ),
    ]
