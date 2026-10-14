def register(model_cls, config_cls=None):
    """Register *model_cls* with eav, optionally with a custom *config_cls*."""
    from eav.registry import Registry  # noqa: PLC0415

    Registry.register(model_cls, config_cls)


def unregister(model_cls):
    """Unregister *model_cls* from eav."""
    from eav.registry import Registry  # noqa: PLC0415

    Registry.unregister(model_cls)
