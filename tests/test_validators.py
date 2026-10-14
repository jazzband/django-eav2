from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from eav import validators


@pytest.mark.parametrize(
    "validator",
    [validators.validate_int, validators.validate_float],
)
@pytest.mark.parametrize("candidate", [None, [], {}, object()])
def test_numeric_validators_reject_non_numbers_with_validation_error(
    validator,
    candidate,
) -> None:
    with pytest.raises(ValidationError):
        validator(candidate)


@pytest.mark.parametrize(
    ("validator", "candidate"),
    [
        (validators.validate_int, 3),
        (validators.validate_int, "3"),
        (validators.validate_float, 3.5),
        (validators.validate_float, "3.5"),
        (validators.validate_json, {"a": 1}),
        (validators.validate_json, '{"a": 1}'),
        (validators.validate_csv, "a;b"),
        (validators.validate_csv, ["a", "b"]),
    ],
)
def test_validators_accept_valid_candidates(validator, candidate) -> None:
    validator(candidate)


@pytest.mark.parametrize("candidate", ["[1, 2]", "not json", 5, None, [1]])
def test_json_validator_rejects_non_objects(candidate) -> None:
    with pytest.raises(ValidationError):
        validators.validate_json(candidate)
