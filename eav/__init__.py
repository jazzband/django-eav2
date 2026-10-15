from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model


def register(model_cls: type[Model], config_cls: type | None = None) -> None:
    """Register *model_cls* with eav, optionally with a custom *config_cls*."""
    from eav.registry import Registry  # noqa: PLC0415

    Registry.register(model_cls, config_cls)


def unregister(model_cls: type[Model]) -> None:
    """Unregister *model_cls* from eav."""
    from eav.registry import Registry  # noqa: PLC0415

    Registry.unregister(model_cls)
