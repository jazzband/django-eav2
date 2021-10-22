from django.db.models.fields import UUIDField


def get_entity_pk_type(entity_cls) -> str:
    """Returns the entity PK type to use.

    These values map to `models.Value` as potential fields to use to relate
    to the proper entity via the correct PK type.
    """
    if isinstance(entity_cls._meta.pk, UUIDField):
        return 'entity_uuid'
    return 'entity_id'
