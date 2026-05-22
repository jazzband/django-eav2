def register(model_cls, config_cls=None):
    from eav.registry import Registry  # noqa: PLC0415

    Registry.register(model_cls, config_cls)


def unregister(model_cls):
    from eav.registry import Registry  # noqa: PLC0415

    Registry.unregister(model_cls)
