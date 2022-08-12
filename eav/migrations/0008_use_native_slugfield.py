from django.db import migrations, models


class Migration(migrations.Migration):
    """Use Django SlugField() for Attribute.slug."""

    dependencies = [
        ('eav', '0007_alter_value_value_int'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribute',
            name='slug',
            field=models.SlugField(
                help_text='Short unique attribute label',
                unique=True,
                verbose_name='Slug',
            ),
        ),
    ]
