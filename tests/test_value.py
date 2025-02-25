import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from eav.models import Attribute, Value
from test_project.models import Doctor, Patient


@pytest.fixture
def patient_ct() -> ContentType:
    """Return the content type for the Patient model."""
    return ContentType.objects.get_for_model(Patient)


@pytest.fixture
def doctor_ct() -> ContentType:
    """Return the content type for the Doctor model."""
    # We use Doctor model for UUID tests since it already uses UUID as primary key
    return ContentType.objects.get_for_model(Doctor)


@pytest.fixture
def attribute() -> Attribute:
    """Create and return a test attribute."""
    return Attribute.objects.create(
        name="test_attribute",
        datatype="text",
    )


@pytest.fixture
def patient() -> Patient:
    """Create and return a patient with integer PK."""
    # Patient model uses auto-incrementing integer primary keys
    return Patient.objects.create(name="Patient with Int PK")


@pytest.fixture
def doctor() -> Doctor:
    """Create and return a doctor with UUID PK."""
    # Doctor model uses UUID primary keys, ideal for testing entity_uuid constraints
    return Doctor.objects.create(name="Doctor with UUID PK")


class TestValueModelValidation:
    """Test Value model Python-level validation (via full_clean in save)."""

    @pytest.mark.django_db
    def test_unique_entity_id_validation(
        self,
        patient_ct: ContentType,
        attribute: Attribute,
        patient: Patient,
    ) -> None:
        """
        Test that model validation prevents duplicate entity_id values.

        The model's save() method calls full_clean() which should detect the
        duplicate before it hits the database constraint.
        """
        # Create first value - this should succeed
        Value.objects.create(
            entity_ct=patient_ct,
            entity_id=patient.id,
            attribute=attribute,
            value_text="First value",
        )

        # Try to create a second value with the same entity_ct, attribute, and entity_id
        # This should fail with ValidationError from full_clean()
        with pytest.raises(ValidationError) as excinfo:
            Value.objects.create(
                entity_ct=patient_ct,
                entity_id=patient.id,
                attribute=attribute,
                value_text="Second value",
            )

        # Verify the error message indicates uniqueness violation
        assert "already exists" in str(excinfo.value)

    @pytest.mark.django_db
    def test_unique_entity_uuid_validation(
        self,
        doctor_ct: ContentType,
        attribute: Attribute,
        doctor: Doctor,
    ) -> None:
        """
        Test that model validation prevents duplicate entity_uuid values.

        The model's full_clean() should detect the duplicate before it hits
        the database constraint.
        """
        # Create first value with UUID - this should succeed
        Value.objects.create(
            entity_ct=doctor_ct,
            entity_uuid=doctor.id,
            attribute=attribute,
            value_text="First UUID value",
        )

        # Try to create a second value with the same entity_ct,
        # attribute, and entity_uuid
        with pytest.raises(ValidationError) as excinfo:
            Value.objects.create(
                entity_ct=doctor_ct,
                entity_uuid=doctor.id,
                attribute=attribute,
                value_text="Second UUID value",
            )

        # Verify the error message indicates uniqueness violation
        assert "already exists" in str(excinfo.value)

    @pytest.mark.django_db
    def test_entity_id_xor_entity_uuid_validation(
        self,
        patient_ct: ContentType,
        attribute: Attribute,
        patient: Patient,
        doctor: Doctor,
    ) -> None:
        """
        Test that model validation enforces XOR between entity_id and entity_uuid.

        The model's full_clean() should detect if both or neither field is provided.
        """
        # Try to create with both ID types
        with pytest.raises(ValidationError):
            Value.objects.create(
                entity_ct=patient_ct,
                entity_id=patient.id,
                entity_uuid=doctor.id,
                attribute=attribute,
                value_text="Both IDs provided",
            )

        # Try to create with neither ID type
        with pytest.raises(ValidationError):
            Value.objects.create(
                entity_ct=patient_ct,
                entity_id=None,
                entity_uuid=None,
                attribute=attribute,
                value_text="No IDs provided",
            )


class TestValueDatabaseConstraints:
    """
    Test Value model database constraints when bypassing model validation.

    These tests use bulk_create() which bypasses the save() method and its
    full_clean() validation, allowing us to test the database constraints directly.
    """

    @pytest.mark.django_db
    def test_unique_entity_id_constraint(
        self,
        patient_ct: ContentType,
        attribute: Attribute,
        patient: Patient,
    ) -> None:
        """
        Test that database constraints prevent duplicate entity_id values.

        Even when bypassing model validation with bulk_create, the database
        constraint should still prevent duplicates.
        """
        # Create first value - this should succeed
        Value.objects.create(
            entity_ct=patient_ct,
            entity_id=patient.id,
            attribute=attribute,
            value_text="First value",
        )

        # Try to bulk create a duplicate value, bypassing model validation
        with pytest.raises(IntegrityError):
            Value.objects.bulk_create(
                [
                    Value(
                        entity_ct=patient_ct,
                        entity_id=patient.id,
                        attribute=attribute,
                        value_text="Second value",
                    ),
                ],
            )

    @pytest.mark.django_db
    def test_unique_entity_uuid_constraint(
        self,
        doctor_ct: ContentType,
        attribute: Attribute,
        doctor: Doctor,
    ) -> None:
        """
        Test that database constraints prevent duplicate entity_uuid values.

        Even when bypassing model validation, the database constraint should
        still prevent duplicates.
        """
        # Create first value with UUID - this should succeed
        Value.objects.create(
            entity_ct=doctor_ct,
            entity_uuid=doctor.id,
            attribute=attribute,
            value_text="First UUID value",
        )

        # Try to bulk create a duplicate value, bypassing model validation
        with pytest.raises(IntegrityError):
            Value.objects.bulk_create(
                [
                    Value(
                        entity_ct=doctor_ct,
                        entity_uuid=doctor.id,
                        attribute=attribute,
                        value_text="Second UUID value",
                    ),
                ],
            )

    @pytest.mark.django_db
    def test_entity_id_and_entity_uuid_constraint(
        self,
        patient_ct: ContentType,
        attribute: Attribute,
        patient: Patient,
        doctor: Doctor,
    ) -> None:
        """
        Test that database constraints prevent having both entity_id and entity_uuid.

        Even when bypassing model validation, the database constraint should
        prevent having both fields set.
        """
        # Try to bulk create with both ID types
        with pytest.raises(IntegrityError):
            Value.objects.bulk_create(
                [
                    Value(
                        entity_ct=patient_ct,
                        entity_id=patient.id,
                        entity_uuid=doctor.id,
                        attribute=attribute,
                        value_text="Both IDs provided",
                    ),
                ],
            )

    @pytest.mark.django_db
    def test_neither_entity_id_nor_entity_uuid_constraint(
        self,
        patient_ct: ContentType,
        attribute: Attribute,
    ) -> None:
        """
        Test that database constraints prevent having neither entity_id nor entity_uuid.

        Even when bypassing model validation, the database constraint should
        prevent having neither field set.
        """
        # Try to bulk create with neither ID type
        with pytest.raises(IntegrityError):
            Value.objects.bulk_create(
                [
                    Value(
                        entity_ct=patient_ct,
                        entity_id=None,
                        entity_uuid=None,
                        attribute=attribute,
                        value_text="No IDs provided",
                    ),
                ],
            )

    @pytest.mark.django_db
    def test_happy_path_constraints(
        self,
        patient_ct: ContentType,
        doctor_ct: ContentType,
        attribute: Attribute,
        patient: Patient,
        doctor: Doctor,
    ) -> None:
        """
        Test that valid values pass both database constraints.

        Values with either entity_id or entity_uuid (but not both) should be accepted.
        """
        # Test with entity_id using bulk_create
        values = Value.objects.bulk_create(
            [
                Value(
                    entity_ct=patient_ct,
                    entity_id=patient.id,
                    attribute=attribute,
                    value_text="Integer ID bulk created",
                ),
            ],
        )
        assert len(values) == 1

        # Test with entity_uuid using bulk_create
        values = Value.objects.bulk_create(
            [
                Value(
                    entity_ct=doctor_ct,
                    entity_uuid=doctor.id,
                    attribute=attribute,
                    value_text="UUID bulk created",
                ),
            ],
        )
        assert len(values) == 1
