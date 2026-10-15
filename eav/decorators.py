"""Pure wrapper functions used as decorators.

Functions in this module should be simple and not involve complex logic.
"""

from collections.abc import Callable
from typing import Any, TypeVar, cast

from django.db.models import Model

from eav import register

_ModelT = TypeVar("_ModelT")


def register_eav(**kwargs: Any) -> Callable[[_ModelT], _ModelT]:
    """Register the decorated ``Model`` class with Django EAV 2.

    Example::

        @register_eav()
        class Author(models.Model):
            pass
    """

    def _model_eav_wrapper(model_class: _ModelT) -> _ModelT:
        if not (isinstance(model_class, type) and issubclass(model_class, Model)):
            raise TypeError("Wrapped class must subclass Model.")
        register(model_class, **kwargs)
        return cast("_ModelT", model_class)

    return _model_eav_wrapper
