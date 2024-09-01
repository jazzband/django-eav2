from django.db import migrations, models


class Migration(migrations.Migration):
    """Update default values and meta options for Attribute and Value models."""

    dependencies = [
        ("eav", "0010_dynamic_pk_type_for_models"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="attribute",
            options={
                "ordering": ("name",),
                "verbose_name": "Attribute",
                "verbose_name_plural": "Attributes",
            },
        ),
        migrations.AlterField(
            model_name="attribute",
            name="description",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Short description",
                max_length=256,
                verbose_name="Description",
            ),
        ),
        migrations.AlterField(
            model_name="value",
            name="value_text",
            field=models.TextField(blank=True, default="", verbose_name="Value text"),
        ),
    ]
