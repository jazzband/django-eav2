from django.db import migrations

from eav.logic.object_pk import get_pk_format


class Migration(migrations.Migration):
    """Use the primary key chosen by ``EAV2_PRIMARY_KEY_FIELD`` for all models."""

    dependencies = [
        ("eav", "0009_enchance_naming"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attribute",
            name="id",
            field=get_pk_format(),
        ),
        migrations.AlterField(
            model_name="enumgroup",
            name="id",
            field=get_pk_format(),
        ),
        migrations.AlterField(
            model_name="enumvalue",
            name="id",
            field=get_pk_format(),
        ),
        migrations.AlterField(
            model_name="value",
            name="id",
            field=get_pk_format(),
        ),
    ]
