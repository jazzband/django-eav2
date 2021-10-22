import uuid

from django.db import migrations, models

from test_project.models import MAX_CHARFIELD_LEN


class Migration(migrations.Migration):
    """Initial migration for test_project."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ExampleMetaclassModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=MAX_CHARFIELD_LEN)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ExampleModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=MAX_CHARFIELD_LEN)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RegisterTestModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=MAX_CHARFIELD_LEN)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=MAX_CHARFIELD_LEN)),
                ('email', models.EmailField(blank=True, max_length=MAX_CHARFIELD_LEN)),
                (
                    'example',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        to='test_project.examplemodel',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='M2MModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=MAX_CHARFIELD_LEN)),
                ('models', models.ManyToManyField(to='test_project.ExampleModel')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Encounter',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('num', models.PositiveSmallIntegerField()),
                (
                    'patient',
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        to='test_project.patient',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Doctor',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('name', models.CharField(max_length=MAX_CHARFIELD_LEN)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
