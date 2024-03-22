from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration to set CharField as default primary key  for all models."""

    dependencies = [
        ('eav', '0010_dynamic_pk_type_for_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribute',
            name='id',
            field=models.CharField(
                editable=False, max_length=255, primary_key=True, serialize=False
            ),
        ),
        migrations.AlterField(
            model_name='enumgroup',
            name='id',
            field=models.CharField(
                editable=False, max_length=255, primary_key=True, serialize=False
            ),
        ),
        migrations.AlterField(
            model_name='enumvalue',
            name='id',
            field=models.CharField(
                editable=False, max_length=255, primary_key=True, serialize=False
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='id',
            field=models.CharField(
                editable=False, max_length=255, primary_key=True, serialize=False
            ),
        ),
    ]
