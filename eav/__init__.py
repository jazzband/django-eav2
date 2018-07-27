__version__ = '0.11.0'

def register(model_cls, config_cls=None):
    from .registry import Registry
    Registry.register(model_cls, config_cls)

def unregister(model_cls):
    from .registry import Registry
    Registry.unregister(model_cls)
