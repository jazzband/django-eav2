from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

def validate_string(value):
    pass

def validate_text(value):
    pass

def validate_float(value):
    try:
        float(value)
    except ValueError:
        raise ValidationError(_(u"Must be a float"))

def validate_int(value):
    try:
        int(value)
    except ValueError:
        raise ValidationError(_(u"Must be an integer"))

def validate_date(value):
    #TODO
    pass

def validate_bool(value):
    pass

def validate_model(value):
    pass

def validate_enum(value):
    pass
