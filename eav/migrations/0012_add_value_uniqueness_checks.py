from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add uniqueness and integrity constraints to the Value model.

    This migration adds database-level constraints to ensure:
    1. Each entity (identified by UUID) can have only one value per attribute
    2. Each entity (identified by integer ID) can have only one value per attribute
    3. Each value must use either entity_id OR entity_uuid, never both or neither

    These constraints ensure data integrity by preventing duplicate attribute values
    for the same entity and enforcing the XOR relationship between the two types of
    entity identification (integer ID vs UUID).
    """

    dependencies = [
        ("eav", "0011_update_defaults_and_meta"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="value",
            constraint=models.UniqueConstraint(
                fields=("entity_ct", "attribute", "entity_uuid"),
                name="unique_entity_uuid_per_attribute",
            ),
        ),
        migrations.AddConstraint(
            model_name="value",
            constraint=models.UniqueConstraint(
                fields=("entity_ct", "attribute", "entity_id"),
                name="unique_entity_id_per_attribute",
            ),
        ),
        migrations.AddConstraint(
            model_name="value",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("entity_id__isnull", False),
                        ("entity_uuid__isnull", True),
                    ),
                    models.Q(
                        ("entity_id__isnull", True),
                        ("entity_uuid__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="ensure_entity_id_xor_entity_uuid",
            ),
        ),
    ]
