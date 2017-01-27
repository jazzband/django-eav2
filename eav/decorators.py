def register_eav(**kwargs):
    """
    Registers the given model(s) classes and wrapped Model class with
    django-eav:

    @register_eav
    class Author(models.Model):
        pass
    """
    from . import register
    from django.db.models import Model

    def _model_eav_wrapper(model_class):
        if not issubclass(model_class, Model):
            raise ValueError('Wrapped class must subclass Model.')
        register(model_class, **kwargs)
        return model_class

    return _model_eav_wrapper