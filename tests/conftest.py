import pytest
from django.apps import apps

import eav


@pytest.fixture(autouse=True)
def _restore_eav_registry():
    """
    Undo any (un)registration a test performed on the test project models.

    Registration is global state, so without this tests pass or fail
    depending on the order they run in.
    """
    models = list(apps.get_app_config("test_project").get_models())
    before = {model: getattr(model, "_eav_config_cls", None) for model in models}

    yield

    for model, config_cls in before.items():
        if getattr(model, "_eav_config_cls", None) is config_cls:
            continue

        eav.unregister(model)
        if config_cls is not None:
            eav.register(model, config_cls)
