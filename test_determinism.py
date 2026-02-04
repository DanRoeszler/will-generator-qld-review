"""
Determinism Tests

Tests that the will generation is deterministic:
- Same payload + same timestamp = identical PDF bytes
- Hash verification works correctly
- No system time calls during rendering
"""

import unittest
import hashlib
from datetime import datetime
from io import BytesIO

from app.context_builder import build_context
from app.clause_renderer import render_document_plan
from app.pdf_generator import generate_pdf_with_footer, verify_pdf_integrity
from app.validation import validate_payload


class TestDeterminism(unittest.TestCase):
    """Test deterministic PDF generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.payload = {
            'eligibility': {
                'confirm_age_over_18': True,
                'confirm_qld': True,
                'confirm_not_legal_advice': True
            },
            'will_maker': {
                'full_name': 'John Determinism Test',
                'dob': '1970-01-15',
                'occupation': 'Software Engineer',
                'address': {
                    'street': '123 Test Street',
                    'suburb': 'Brisbane',
                    'state': 'QLD',
                    'postcode': '4000'
                },
                'email': 'john@test.com',
                'phone': '0412 345 678',
                'relationship_status': 'married'
            },
            'partner': {
                'full_name': 'Jane Test',
                'dob': '1972-03-20',
                'address': {
                    'street': '123 Test Street',
                    'suburb': 'Brisbane',
                    'state': 'QLD',
                    'postcode': '4000'
                }
            },
            'has_children': False,
            'dependants': {
                'has_other_dependants': False
            },
            'executors': {
                'mode': 'one',
                'primary': [
                    {
                        'full_name': 'Robert Executor',
                        'relationship': 'friend',
                        'address': {
                            'street': '456 Executor Ave',
                            'suburb': 'Sydney',
                            'state': 'NSW',
                            'postcode': '2000'
                        }
                    }
                ],
                'backup': {
                    'mode': 'none'
                }
            },
            'beneficiaries': [
                {
                    'id': 'ben_1',
                    'type': 'individual',
                    'full_name': 'Alice Beneficiary',
                    'relationship': 'sister',
                    'address': {
                        'street': '123 Beneficiary St',
                        'suburb': 'Brisbane',
                        'state': 'QLD',
                        'postcode': '4000'
                    },
                    'gift_role': 'residue',
                    'residue_share_percent': 100.0
                }
            ],
            'distribution': {
                'scheme': 'custom_structured'
            },
            'survivorship': {
                'days': 30
            },
            'substitution': {
                'rule': 'to_their_children'
            },
            'minor_trusts': {
                'enabled': False
            },
            'funeral': {
                'enabled': False
            },
            'digital_assets': {
                'enabled': False
            },
            'pets': {
                'enabled': False
            },
            'business': {
                'enabled': False
            },
            'exclusions': {
                'enabled': False
            },
            'life_sustaining': {
                'enabled': False
            },
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True,
                'intended_signing_date': '2024-12-25'
            }
        }
        
        # Fixed timestamp for determinism testing
        self.fixed_timestamp = datetime(2024, 12, 25, 10, 0, 0)
    
    def test_same_payload_same_timestamp_same_pdf(self):
        """Test that same payload + same timestamp = identical PDF."""
        # Validate payload
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid, f"Validation failed: {result.errors}")
        
        # Build context
        context = build_context(self.payload)
        
        # Render document plan
        document_plan = render_document_plan(context)
        
        # Generate PDF twice with same timestamp
        pdf1_bytes, hash1 = generate_pdf_with_footer(
            context, 
            document_plan,
            generation_timestamp=self.fixed_timestamp
        )
        
        pdf2_bytes, hash2 = generate_pdf_with_footer(
            context, 
            document_plan,
            generation_timestamp=self.fixed_timestamp
        )
        
        # PDFs should be byte-for-byte identical
        self.assertEqual(pdf1_bytes, pdf2_bytes, "PDFs should be byte-for-byte identical")
        self.assertEqual(hash1, hash2, "Hashes should be identical")
    
    def test_different_timestamps_same_pdf_with_invariant_mode(self):
        """Test that with invariant mode, different timestamps produce identical PDFs."""
        # Validate payload
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        # Build context
        context = build_context(self.payload)
        document_plan = render_document_plan(context)
        
        # Generate PDF with different timestamps
        timestamp1 = datetime(2024, 12, 25, 10, 0, 0)
        timestamp2 = datetime(2024, 12, 25, 10, 0, 1)  # 1 second later
        
        pdf1_bytes, hash1 = generate_pdf_with_footer(
            context, document_plan, generation_timestamp=timestamp1
        )
        pdf2_bytes, hash2 = generate_pdf_with_footer(
            context, document_plan, generation_timestamp=timestamp2
        )
        
        # With invariant mode enabled, PDFs should be identical regardless of timestamp
        # This ensures determinism - the core requirement
        self.assertEqual(pdf1_bytes, pdf2_bytes, "PDFs should be identical with invariant mode")
    
    def test_hash_verification(self):
        """Test that PDF hash verification works correctly."""
        # Validate and generate
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        document_plan = render_document_plan(context)
        
        pdf_bytes, expected_hash = generate_pdf_with_footer(
            context, document_plan, generation_timestamp=self.fixed_timestamp
        )
        
        # Verify hash
        is_valid = verify_pdf_integrity(pdf_bytes, expected_hash)
        self.assertTrue(is_valid, "Hash verification should succeed for valid PDF")
        
        # Modify PDF and verify hash fails
        modified_bytes = pdf_bytes[:100] + b'X' + pdf_bytes[101:]
        is_valid = verify_pdf_integrity(modified_bytes, expected_hash)
        self.assertFalse(is_valid, "Hash verification should fail for modified PDF")
    
    def test_stable_hash_algorithm(self):
        """Test that hash algorithm produces consistent results."""
        # Validate and generate
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        document_plan = render_document_plan(context)
        
        pdf_bytes, _ = generate_pdf_with_footer(
            context, document_plan, generation_timestamp=self.fixed_timestamp
        )
        
        # Calculate hash manually
        manual_hash = hashlib.sha256(pdf_bytes).hexdigest()
        
        # Generate again
        _, generated_hash = generate_pdf_with_footer(
            context, document_plan, generation_timestamp=self.fixed_timestamp
        )
        
        # Hashes should match
        self.assertEqual(manual_hash, generated_hash)
    
    def test_multiple_runs_consistency(self):
        """Test consistency across multiple generation runs."""
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        document_plan = render_document_plan(context)
        
        hashes = []
        for _ in range(5):
            _, hash_value = generate_pdf_with_footer(
                context, document_plan, generation_timestamp=self.fixed_timestamp
            )
            hashes.append(hash_value)
        
        # All hashes should be identical
        self.assertEqual(len(set(hashes)), 1, "All hashes should be identical")


class TestDeterminismWithComplexPayload(unittest.TestCase):
    """Test determinism with complex payloads."""
    
    def setUp(self):
        """Set up complex test payload."""
        self.payload = {
            'eligibility': {
                'confirm_age_over_18': True,
                'confirm_qld': True,
                'confirm_not_legal_advice': True
            },
            'will_maker': {
                'full_name': 'Complex Test Person',
                'dob': '1965-05-20',
                'occupation': 'Business Owner',
                'address': {
                    'street': '789 Complex Road, Suite 100',
                    'suburb': 'Gold Coast',
                    'state': 'QLD',
                    'postcode': '4217'
                },
                'email': 'complex@test.com',
                'phone': '07 5555 1234',
                'relationship_status': 'married'
            },
            'partner': {
                'full_name': 'Spouse Person',
                'dob': '1968-08-12',
                'address': {
                    'street': '789 Complex Road, Suite 100',
                    'suburb': 'Gold Coast',
                    'state': 'QLD',
                    'postcode': '4217'
                }
            },
            'has_children': True,
            'children': [
                {
                    'full_name': 'Child One',
                    'dob': '1995-03-15',
                    'relationship_type': 'biological',
                    'is_expected_to_be_minor_at_death': False,
                    'special_needs': False
                },
                {
                    'full_name': 'Child Two',
                    'dob': '2005-07-22',
                    'relationship_type': 'biological',
                    'is_expected_to_be_minor_at_death': True,
                    'special_needs': False
                }
            ],
            'dependants': {
                'has_other_dependants': False
            },
            'executors': {
                'mode': 'two_joint',
                'primary': [
                    {
                        'full_name': 'First Executor',
                        'relationship': 'solicitor',
                        'address': {
                            'street': '100 Legal Street',
                            'suburb': 'Brisbane',
                            'state': 'QLD',
                            'postcode': '4000'
                        }
                    },
                    {
                        'full_name': 'Second Executor',
                        'relationship': 'accountant',
                        'address': {
                            'street': '200 Finance Ave',
                            'suburb': 'Sydney',
                            'state': 'NSW',
                            'postcode': '2000'
                        }
                    }
                ],
                'backup': {
                    'mode': 'one',
                    'list': [
                        {
                            'full_name': 'Backup Executor',
                            'relationship': 'friend',
                            'address': {
                                'street': '500 Backup St',
                                'suburb': 'Brisbane',
                                'state': 'QLD',
                                'postcode': '4000'
                            }
                        }
                    ]
                }
            },
            'guardianship': {
                'appoint_guardian': True,
                'guardian': {
                    'full_name': 'Guardian Person',
                    'relationship': 'sibling',
                    'address': {
                        'street': '300 Guardian St',
                        'suburb': 'Melbourne',
                        'state': 'VIC',
                        'postcode': '3000'
                    }
                },
                'backup_guardian': {
                    'mode': 'none'
                }
            },
            'beneficiaries': [
                {
                    'id': 'ben_partner',
                    'type': 'individual',
                    'full_name': 'Spouse Person',
                    'relationship': 'partner',
                    'address': {
                        'street': '789 Complex Road',
                        'suburb': 'Gold Coast',
                        'state': 'QLD',
                        'postcode': '4217'
                    },
                    'gift_role': 'residue',
                    'residue_share_percent': 50.0
                },
                {
                    'id': 'ben_child1',
                    'type': 'individual',
                    'full_name': 'Child One',
                    'relationship': 'child',
                    'address': {
                        'street': '100 Child St',
                        'suburb': 'Brisbane',
                        'state': 'QLD',
                        'postcode': '4000'
                    },
                    'gift_role': 'residue',
                    'residue_share_percent': 25.0
                },
                {
                    'id': 'ben_child2',
                    'type': 'individual',
                    'full_name': 'Child Two',
                    'relationship': 'child',
                    'address': {
                        'street': '200 Child St',
                        'suburb': 'Brisbane',
                        'state': 'QLD',
                        'postcode': '4000'
                    },
                    'gift_role': 'residue',
                    'residue_share_percent': 25.0
                },
                {
                    'id': 'ben_charity',
                    'type': 'charity',
                    'full_name': 'Test Charity Ltd',
                    'relationship': 'charity',
                    'abn': '12345678901',
                    'address': {
                        'street': '300 Charity St',
                        'suburb': 'Brisbane',
                        'state': 'QLD',
                        'postcode': '4000'
                    },
                    'gift_role': 'specific_cash',
                    'cash_amount': 10000.0
                }
            ],
            'specific_gifts': [
                {
                    'beneficiary_id': 'ben_charity',
                    'gift_type': 'cash',
                    'cash_amount': 10000.0
                }
            ],
            'distribution': {
                'scheme': 'custom_structured'
            },
            'survivorship': {
                'days': 30
            },
            'substitution': {
                'rule': 'to_their_children'
            },
            'minor_trusts': {
                'enabled': True,
                'vesting_age': 21,
                'trustee_mode': 'executors_as_trustees'
            },
            'funeral': {
                'enabled': True,
                'preference': 'burial',
                'notes': 'Simple ceremony preferred'
            },
            'digital_assets': {
                'enabled': True,
                'authority': True,
                'categories': ['email', 'social_media', 'cloud_storage'],
                'instructions_location': 'With my solicitor'
            },
            'pets': {
                'enabled': True,
                'count': 2,
                'summary': 'Two dogs: Max and Bella',
                'carer_mode': 'new_person',
                'carer_name': 'Pet Carer',
                'carer_address': {
                    'street': '400 Pet Lane',
                    'suburb': 'Adelaide',
                    'state': 'SA',
                    'postcode': '5000'
                },
                'cash_gift': 5000.0
            },
            'business': {
                'enabled': False
            },
            'exclusions': {
                'enabled': False
            },
            'life_sustaining': {
                'enabled': True,
                'template': 'no_prolong',
                'values': ['no_prolong_terminal', 'no_prolong_pvs']
            },
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True,
                'intended_signing_date': '2024-12-25'
            }
        }
        
        self.fixed_timestamp = datetime(2024, 12, 25, 10, 0, 0)
    
    def test_complex_payload_determinism(self):
        """Test determinism with complex payload."""
        # Validate
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid, f"Validation failed: {result.errors}")
        
        # Build context
        context = build_context(self.payload)
        
        # Render document plan
        document_plan = render_document_plan(context)
        
        # Generate PDF multiple times
        hashes = []
        for _ in range(3):
            _, hash_value = generate_pdf_with_footer(
                context, document_plan, generation_timestamp=self.fixed_timestamp
            )
            hashes.append(hash_value)
        
        # All hashes should be identical
        self.assertEqual(len(set(hashes)), 1, "Complex payload should produce deterministic output")


if __name__ == '__main__':
    unittest.main()
