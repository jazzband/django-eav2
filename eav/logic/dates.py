"""Turning dates into the datetimes the ``value_date`` column stores."""

from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.utils import timezone


def as_datetime(candidate: object) -> object:
    """
    Return *candidate* as a datetime if it is a plain date, else unchanged.

    A date becomes midnight in the default timezone, as Django's own
    ``DateTimeField`` does, but without its warning about naive datetimes.
    """
    if isinstance(candidate, dt.datetime) or not isinstance(candidate, dt.date):
        return candidate

    midnight = dt.datetime.combine(candidate, dt.time.min)
    return timezone.make_aware(midnight) if settings.USE_TZ else midnight
