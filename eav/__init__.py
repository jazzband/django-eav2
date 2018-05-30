VERSION = (0, 9, 2)

def get_version():
    version = "%s.%s" % (VERSION[0], VERSION[1])
    if VERSION[2] != 0:
        version = "%s.%s" % (version, VERSION[2])
    return version

__version__ = get_version()


def register(model_cls, config_cls=None):
    from .registry import Registry
    Registry.register(model_cls, config_cls)

def unregister(model_cls):
    from .registry import Registry
    Registry.unregister(model_cls)
