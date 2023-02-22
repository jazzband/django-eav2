from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations, models

from eav.fields import CSVField


class Migration(migrations.Migration):
    """Define verbose naming for models and fields."""

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('eav', '0008_use_native_slugfield'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='attribute',
            options={
                'ordering': ['name'],
                'verbose_name': 'Attribute',
                'verbose_name_plural': 'Attributes',
            },
        ),
        migrations.AlterModelOptions(
            name='enumgroup',
            options={
                'verbose_name': 'EnumGroup',
                'verbose_name_plural': 'EnumGroups',
            },
        ),
        migrations.AlterModelOptions(
            name='enumvalue',
            options={
                'verbose_name': 'EnumValue',
                'verbose_name_plural': 'EnumValues',
            },
        ),
        migrations.AlterModelOptions(
            name='value',
            options={'verbose_name': 'Value', 'verbose_name_plural': 'Values'},
        ),
        migrations.AlterField(
            model_name='attribute',
            name='entity_ct',
            field=models.ManyToManyField(
                blank=True,
                to='contenttypes.contenttype',
                verbose_name='Entity content type',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='entity_ct',
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name='value_entities',
                to='contenttypes.contenttype',
                verbose_name='Entity ct',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='entity_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='Entity id',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='entity_uuid',
            field=models.UUIDField(
                blank=True,
                null=True,
                verbose_name='Entity uuid',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='generic_value_ct',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='value_values',
                to='contenttypes.contenttype',
                verbose_name='Generic value content type',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='generic_value_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='Generic value id',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_bool',
            field=models.BooleanField(
                blank=True,
                null=True,
                verbose_name='Value bool',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_csv',
            field=CSVField(
                blank=True,
                default='',
                null=True,
                verbose_name='Value CSV',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Value date',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_enum',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='eav_values',
                to='eav.enumvalue',
                verbose_name='Value enum',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_float',
            field=models.FloatField(
                blank=True,
                null=True,
                verbose_name='Value float',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_int',
            field=models.BigIntegerField(
                blank=True,
                null=True,
                verbose_name='Value int',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_json',
            field=models.JSONField(
                blank=True,
                default=dict,
                encoder=DjangoJSONEncoder,
                null=True,
                verbose_name='Value JSON',
            ),
        ),
        migrations.AlterField(
            model_name='value',
            name='value_text',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Value text',
            ),
        ),
    ]
