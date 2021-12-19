from django.db import migrations, models


class Migration(migrations.Migration):
    """Convert Value.value_int to BigInteger."""

    dependencies = [
        ('eav', '0006_add_entity_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='value',
            name='value_int',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
