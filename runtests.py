#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests.queries',
                                      'tests.registry',
                                      'tests.data_validation',
                                      'tests.limiting_attributes',
                                      'tests.misc_models',
                                      'tests.set_and_get'])
    sys.exit(bool(failures))
