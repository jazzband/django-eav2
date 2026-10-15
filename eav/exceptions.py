class IllegalAssignmentException(Exception):  # noqa: N818
    """An attempt to assign a value to an attribute the entity cannot have."""


class RemovedInEav3Warning(FutureWarning):
    """A feature that django-eav2 3.0 removes.

    It is a ``FutureWarning`` so Python shows it by default, including outside of
    ``__main__``, where a ``DeprecationWarning`` would stay hidden.
    """
