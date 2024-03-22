from django.core.exceptions import ValidationError
from django.forms import Textarea
from django.test import TestCase
from eav.widgets import CSVWidget

class TestCSVWidget(TestCase):
    def test_prep_value_string(self):
        self._extracted_from_test_prep_value_empty_2("Test Value")

    def test_prep_value_list(self):
        widget = CSVWidget()
        value = ["Value 1", "Value 2", "Value 3"]
        self.assertEqual(widget.prep_value(value), "Value 1;Value 2;Value 3")

    def test_prep_value_empty(self):
        self._extracted_from_test_prep_value_empty_2("")

    # TODO Rename this here and in `test_prep_value_string` and `test_prep_value_empty`
    def _extracted_from_test_prep_value_empty_2(self, arg0):
        widget = CSVWidget()
        value = arg0
        self.assertEqual(widget.prep_value(value), arg0)

    def test_prep_value_invalid(self):
        widget = CSVWidget()
        value = 123  # An invalid value
        with self.assertRaises(ValidationError):
            widget.prep_value(value)

    def test_render(self):
        widget = CSVWidget()
        name = "test_field"
        value = ["Value 1", "Value 2", "Value 3"]
        rendered_widget = widget.render(name, value)
        # You can add more specific assertions based on the expected output
        self.assertIsInstance(rendered_widget, str)
        self.assertIn("Value 1", rendered_widget)
        self.assertIn("Value 2", rendered_widget)
        self.assertIn("Value 3", rendered_widget)
