def register(model_cls, config_cls=None):
    from eav.registry import Registry

    Registry.register(model_cls, config_cls)


def unregister(model_cls):
    from eav.registry import Registry

    Registry.unregister(model_cls)
