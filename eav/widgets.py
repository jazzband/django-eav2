from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.widgets import Textarea

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.forms.renderers import BaseRenderer
    from django.utils.safestring import SafeString

EMPTY_VALUES = (*validators.EMPTY_VALUES, "[]")


class CSVWidget(Textarea):
    """A text area for a list of values joined by a separator."""

    @property
    def is_hidden(self) -> bool:
        """Whether the widget is hidden, which it never is."""
        return False

    def prep_value(self, value: object) -> str:
        """Prepare value before effectively render widget."""
        if value in EMPTY_VALUES:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ";".join(value)
        raise ValidationError("Invalid format.")

    def render(
        self,
        name: str,
        value: Any,
        attrs: dict[str, Any] | None = None,
        renderer: BaseRenderer | None = None,
    ) -> SafeString:
        """Render the widget with the list as separated text."""
        return super().render(name, self.prep_value(value), attrs, renderer)

    def value_from_datadict(
        self,
        data: Mapping[str, Any],
        files: Mapping[str, Any],
        name: str,
    ) -> Any:
        """
        Return the value of this widget or None.

        Since we're only given the value of the entity name and the data dict
        contains the '_eav_config_cls' (which we don't have access to) as the
        key, we need to loop through each field checking if the eav attribute
        exists with the given 'name'.
        """
        for data_value in data.values():
            widget_value = getattr(data_value, name, None)
            if widget_value is not None:
                return widget_value

        return None
