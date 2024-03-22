from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration to use BigAutoField as default for all models."""

    dependencies = [
        ('eav', '0009_enchance_naming'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribute',
            name='id',
            field=models.BigAutoField(
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name='enumgroup',
            name='id',
            field=models.BigAutoField(
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name='enumvalue',
            name='id',
            field=models.BigAutoField(
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='id',
            field=models.BigAutoField(
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
