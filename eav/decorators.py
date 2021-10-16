"""
This module contains pure wrapper functions used as decorators.
Functions in this module should be simple and not involve complex logic.
"""


def register_eav(**kwargs):
    """
    Registers the given model(s) classes and wrapped ``Model`` class with
    Django EAV 2::

        @register_eav
        class Author(models.Model):
            pass
    """
    from django.db.models import Model

    from eav import register

    def _model_eav_wrapper(model_class):
        if not issubclass(model_class, Model):
            raise ValueError('Wrapped class must subclass Model.')
        register(model_class, **kwargs)
        return model_class

    return _model_eav_wrapper
