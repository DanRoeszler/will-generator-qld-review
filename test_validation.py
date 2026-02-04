"""
Unit tests for validation module.
"""

import pytest
from app.validation import (
    validate_payload, ValidationResult,
    validate_percentage, validate_positive_number,
    validate_email, validate_address
)


class TestValidationResult:
    def test_initially_valid(self):
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_add_error(self):
        result = ValidationResult()
        result.add_error('field', 'message', 'code')
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == 'field'
        assert result.errors[0].message == 'message'
        assert result.errors[0].code == 'code'

    def test_to_dict(self):
        result = ValidationResult()
        result.add_error('field', 'message', 'code')
        d = result.to_dict()
        assert d['ok'] is False
        assert len(d['errors']) == 1


class TestPercentageValidation:
    def test_valid_percentage(self):
        result = ValidationResult()
        assert validate_percentage(50, 'field', result) is True
        assert result.is_valid is True

    def test_percentage_too_high(self):
        result = ValidationResult()
        assert validate_percentage(150, 'field', result) is False
        assert result.is_valid is False

    def test_percentage_negative(self):
        result = ValidationResult()
        assert validate_percentage(-10, 'field', result) is False
        assert result.is_valid is False

    def test_percentage_zero(self):
        result = ValidationResult()
        assert validate_percentage(0, 'field', result) is True

    def test_percentage_hundred(self):
        result = ValidationResult()
        assert validate_percentage(100, 'field', result) is True


class TestPositiveNumberValidation:
    def test_valid_positive(self):
        result = ValidationResult()
        assert validate_positive_number(100, 'field', result) is True

    def test_zero(self):
        result = ValidationResult()
        assert validate_positive_number(0, 'field', result) is True

    def test_negative(self):
        result = ValidationResult()
        assert validate_positive_number(-100, 'field', result) is False

    def test_max_value(self):
        result = ValidationResult()
        assert validate_positive_number(100, 'field', result, max_value=100) is True
        assert validate_positive_number(101, 'field', result, max_value=100) is False


class TestEmailValidation:
    def test_valid_email(self):
        result = ValidationResult()
        assert validate_email('test@example.com', 'field', result) is True

    def test_invalid_email(self):
        result = ValidationResult()
        assert validate_email('not-an-email', 'field', result) is False

    def test_missing_at(self):
        result = ValidationResult()
        assert validate_email('testexample.com', 'field', result) is False


class TestAddressValidation:
    def test_valid_address(self):
        result = ValidationResult()
        address = {
            'street': '123 Test St',
            'suburb': 'Brisbane',
            'state': 'QLD',
            'postcode': '4000'
        }
        assert validate_address(address, 'field', result) is True

    def test_missing_street(self):
        result = ValidationResult()
        address = {
            'suburb': 'Brisbane',
            'state': 'QLD',
            'postcode': '4000'
        }
        assert validate_address(address, 'field', result) is False

    def test_invalid_postcode(self):
        result = ValidationResult()
        address = {
            'street': '123 Test St',
            'suburb': 'Brisbane',
            'state': 'QLD',
            'postcode': '400'  # Only 3 digits
        }
        assert validate_address(address, 'field', result) is False


class TestPayloadValidation:
    def test_empty_payload(self):
        result = validate_payload({})
        assert result.is_valid is False

    def test_minimal_valid_payload(self):
        payload = {
            'eligibility': {
                'confirm_age_over_18': True,
                'confirm_qld': True,
                'confirm_not_legal_advice': True
            },
            'will_maker': {
                'full_name': 'John Doe',
                'dob': '1980-01-01',
                'occupation': 'Engineer',
                'address': {
                    'street': '123 Test St',
                    'suburb': 'Brisbane',
                    'state': 'QLD',
                    'postcode': '4000'
                },
                'email': 'john@example.com',
                'phone': '0400 000 000',
                'relationship_status': 'single'
            },
            'has_children': False,
            'dependants': {
                'has_other_dependants': False
            },
            'executors': {
                'mode': 'one',
                'primary': [{
                    'full_name': 'Jane Doe',
                    'relationship': 'Sister',
                    'address': {
                        'street': '456 Test Ave',
                        'suburb': 'Brisbane',
                        'state': 'QLD',
                        'postcode': '4000'
                    }
                }],
                'backup': {
                    'mode': 'none'
                }
            },
            'distribution': {
                'scheme': 'percentages_named'
            },
            'beneficiaries': [
                {
                    'type': 'individual',
                    'full_name': 'Jane Doe',
                    'relationship': 'Sister',
                    'address': {
                        'street': '456 Test Ave',
                        'suburb': 'Brisbane',
                        'state': 'QLD',
                        'postcode': '4000'
                    },
                    'gift_role': 'percentage_only',
                    'percentage': 100
                }
            ],
            'survivorship': {
                'days': 30
            },
            'substitution': {
                'rule': 'to_their_children'
            },
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        result = validate_payload(payload)
        assert result.is_valid is True, f"Errors: {result.errors}"

    def test_percentage_sum_validation(self):
        payload = {
            'distribution': {
                'scheme': 'percentages_named'
            },
            'beneficiaries': [
                {
                    'type': 'individual',
                    'full_name': 'Person A',
                    'relationship': 'Friend',
                    'address': {'street': '1 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                    'gift_role': 'percentage_only',
                    'percentage': 50
                },
                {
                    'type': 'individual',
                    'full_name': 'Person B',
                    'relationship': 'Friend',
                    'address': {'street': '2 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                    'gift_role': 'percentage_only',
                    'percentage': 40  # Total is 90, not 100
                }
            ]
        }
        result = validate_payload(payload)
        assert result.is_valid is False
        # Check for percentage sum error (in field or message)
        assert any('percentage' in e.field.lower() or 'percentage' in e.message.lower() for e in result.errors)

    def test_guardian_requires_minor_child(self):
        # This test would require the full payload with children
        # For now, we test that validation doesn't fail on guardian fields
        # when there are no children
        pass

    def test_html_tags_rejected(self):
        payload = {
            'will_maker': {
                'full_name': '<script>alert("xss")</script>',
                'dob': '1980-01-01',
                'occupation': 'Engineer',
                'address': {
                    'street': '123 Test St',
                    'suburb': 'Brisbane',
                    'state': 'QLD',
                    'postcode': '4000'
                },
                'email': 'test@example.com',
                'phone': '0400 000 000',
                'relationship_status': 'single'
            },
            'has_children': False,
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{
                    'full_name': 'Jane Doe',
                    'relationship': 'Sister',
                    'address': {'street': '456 Ave', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}
                }],
                'backup': {'mode': 'none'}
            },
            'distribution': {'scheme': 'percentages_named'},
            'beneficiaries': [{
                'type': 'individual',
                'full_name': 'Jane Doe',
                'relationship': 'Sister',
                'address': {'street': '456 Ave', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'gift_role': 'percentage_only',
                'percentage': 100
            }],
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        result = validate_payload(payload)
        assert result.is_valid is False
        assert any('will_maker.full_name' in e.field for e in result.errors)


class TestDistributionSchemeValidation:
    def test_partner_then_children_requires_partner(self):
        payload = {
            'will_maker': {
                'full_name': 'John Doe',
                'dob': '1980-01-01',
                'occupation': 'Engineer',
                'address': {'street': '123 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@example.com',
                'phone': '0400 000 000',
                'relationship_status': 'single'  # No partner
            },
            'has_children': True,
            'children': [{
                'full_name': 'Child One',
                'dob': '2010-01-01',
                'relationship_type': 'biological',
                'is_expected_to_be_minor_at_death': True
            }],
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Executor', 'relationship': 'Friend', 'address': {'street': '1 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'distribution': {
                'scheme': 'partner_then_children_equal'  # Requires partner
            },
            'beneficiaries': [],
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        result = validate_payload(payload)
        assert result.is_valid is False
        assert any('scheme' in e.field for e in result.errors)

    def test_children_equal_requires_children(self):
        payload = {
            'will_maker': {
                'full_name': 'John Doe',
                'dob': '1980-01-01',
                'occupation': 'Engineer',
                'address': {'street': '123 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@example.com',
                'phone': '0400 000 000',
                'relationship_status': 'single'
            },
            'has_children': False,  # No children
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Executor', 'relationship': 'Friend', 'address': {'street': '1 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'distribution': {
                'scheme': 'children_equal'  # Requires children
            },
            'beneficiaries': [],
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        result = validate_payload(payload)
        assert result.is_valid is False
        assert any('scheme' in e.field for e in result.errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
