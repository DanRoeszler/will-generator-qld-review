"""
Explainability Tests

Tests for the explainability module:
- Will summary generation
- Risk warning detection
- Clause explainability
- What will does NOT cover
"""

import unittest

from app.context_builder import build_context, WillContext
from app.explainability import (
    generate_will_summary, generate_clause_explainability,
    generate_execution_checklist_summary, RiskLevel, RiskWarning,
    WhatWillDoesNotCover
)
from app.validation import validate_payload


class TestWillSummaryGeneration(unittest.TestCase):
    """Test will summary generation."""
    
    def setUp(self):
        """Set up test payload."""
        self.payload = {
            'eligibility': {
                'confirm_age_over_18': True,
                'confirm_qld': True,
                'confirm_not_legal_advice': True
            },
            'will_maker': {
                'full_name': 'Test Person',
                'dob': '1970-01-15',
                'occupation': 'Engineer',
                'address': {
                    'street': '123 Test St',
                    'suburb': 'Brisbane',
                    'state': 'QLD',
                    'postcode': '4000'
                },
                'email': 'test@example.com',
                'phone': '0412 345 678',
                'relationship_status': 'married'
            },
            'partner': {
                'full_name': 'Spouse Person',
                'dob': '1972-03-20',
                'address': {
                    'street': '123 Test St',
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
                        'full_name': 'Executor One',
                        'relationship': 'friend',
                        'address': {
                            'street': '456 Exec Ave',
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
                    'full_name': 'Beneficiary One',
                    'relationship': 'sibling',
                    'address': {
                        'street': '789 St',
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
            'minor_trusts': {'enabled': False},
            'funeral': {'enabled': False},
            'digital_assets': {'enabled': False},
            'pets': {'enabled': False},
            'business': {'enabled': False},
            'exclusions': {'enabled': False},
            'life_sustaining': {'enabled': False},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True,
                'intended_signing_date': '2024-12-25'
            }
        }
    
    def test_summary_has_will_maker_name(self):
        """Test that summary includes will maker name."""
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        summary = generate_will_summary(context)
        
        self.assertEqual(summary.will_maker_name, 'Test Person')
    
    def test_summary_has_executor_sections(self):
        """Test that summary includes executor information."""
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        summary = generate_will_summary(context)
        
        # Should have executor section (titled "Who Will Manage Your Estate")
        executor_sections = [s for s in summary.sections if 'Manage Your Estate' in s.title or 'Executor' in s.title]
        self.assertTrue(len(executor_sections) > 0)
    
    def test_summary_has_distribution_section(self):
        """Test that summary includes distribution information."""
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        summary = generate_will_summary(context)
        
        # Should have distribution section
        dist_sections = [s for s in summary.sections if 'Distribution' in s.title]
        self.assertTrue(len(dist_sections) > 0)
    
    def test_summary_has_not_covered_items(self):
        """Test that summary includes what will does NOT cover."""
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        summary = generate_will_summary(context)
        
        # Should have not_covered items
        self.assertTrue(len(summary.not_covered) > 0)
        
        # Check for common exclusions
        categories = [n.category for n in summary.not_covered]
        self.assertIn('Superannuation', categories)
        self.assertIn('Jointly Owned Property', categories)
    
    def test_summary_to_dict_structure(self):
        """Test that to_dict produces correct structure."""
        result = validate_payload(self.payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(self.payload)
        summary = generate_will_summary(context)
        
        d = summary.to_dict()
        
        self.assertIn('overview', d)
        self.assertIn('key_facts', d)
        self.assertIn('sections', d)
        self.assertIn('not_covered', d)
        self.assertIn('warnings', d)
        self.assertIn('warning_counts', d)
        
        self.assertIn('will_maker_name', d['overview'])
        self.assertIn('executor_count', d['key_facts'])
        self.assertIn('info', d['warning_counts'])
        self.assertIn('warning', d['warning_counts'])
        self.assertIn('critical', d['warning_counts'])


class TestRiskWarnings(unittest.TestCase):
    """Test risk warning generation."""
    
    def test_warning_single_executor(self):
        """Test warning for single executor."""
        payload = {
            'eligibility': {'confirm_age_over_18': True, 'confirm_qld': True, 'confirm_not_legal_advice': True},
            'will_maker': {
                'full_name': 'Test',
                'dob': '1970-01-15',
                'occupation': 'Engineer',
                'address': {'street': '123 Test St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@test.com',
                'phone': '0412345678',
                'relationship_status': 'single'
            },
            'has_children': False,
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Only Executor', 'relationship': 'friend', 'address': {'street': '456 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'beneficiaries': [
                {'id': 'ben_1', 'type': 'individual', 'full_name': 'Beneficiary', 'relationship': 'sibling',
                 'address': {'street': '789 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                 'gift_role': 'residue', 'residue_share_percent': 100.0}
            ],
            'distribution': {'scheme': 'custom_structured'},
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'minor_trusts': {'enabled': False},
            'funeral': {'enabled': False},
            'digital_assets': {'enabled': False},
            'pets': {'enabled': False},
            'business': {'enabled': False},
            'exclusions': {'enabled': False},
            'life_sustaining': {'enabled': False},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        
        result = validate_payload(payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(payload)
        summary = generate_will_summary(context)
        
        # Should have single executor warning
        single_exec_warnings = [w for w in summary.warnings if 'Single Executor' in w.title]
        self.assertTrue(len(single_exec_warnings) > 0)
        self.assertEqual(single_exec_warnings[0].level, RiskLevel.INFO)
    
    def test_critical_warning_no_guardian_for_minors(self):
        """Test critical warning for minor children without guardian."""
        payload = {
            'eligibility': {'confirm_age_over_18': True, 'confirm_qld': True, 'confirm_not_legal_advice': True},
            'will_maker': {
                'full_name': 'Test',
                'dob': '1970-01-15',
                'occupation': 'Engineer',
                'address': {'street': '123 Test St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@test.com',
                'phone': '0412345678',
                'relationship_status': 'single'
            },
            'has_children': True,
            'children': [
                {'full_name': 'Minor Child', 'dob': '2015-01-01', 'relationship_type': 'biological', 'is_expected_to_be_minor_at_death': True, 'special_needs': False}
            ],
            'dependants': {'has_other_dependants': False},
            'guardianship': {
                'appoint_guardian': False
            },
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Executor', 'relationship': 'friend', 'address': {'street': '456 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'beneficiaries': [
                {'id': 'ben_1', 'type': 'individual', 'full_name': 'Beneficiary', 'relationship': 'sibling',
                 'address': {'street': '789 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                 'gift_role': 'residue', 'residue_share_percent': 100.0}
            ],
            'distribution': {'scheme': 'custom_structured'},
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'minor_trusts': {'enabled': False},
            'funeral': {'enabled': False},
            'digital_assets': {'enabled': False},
            'pets': {'enabled': False},
            'business': {'enabled': False},
            'exclusions': {'enabled': False},
            'life_sustaining': {'enabled': False},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        
        result = validate_payload(payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(payload)
        summary = generate_will_summary(context)
        
        # Should have critical warning about guardian
        guardian_warnings = [w for w in summary.warnings if 'Guardian' in w.title]
        self.assertTrue(len(guardian_warnings) > 0)
        self.assertEqual(guardian_warnings[0].level, RiskLevel.CRITICAL)
    
    def test_warning_no_backup_executors(self):
        """Test warning for no backup executors."""
        payload = {
            'eligibility': {'confirm_age_over_18': True, 'confirm_qld': True, 'confirm_not_legal_advice': True},
            'will_maker': {
                'full_name': 'Test',
                'dob': '1970-01-15',
                'occupation': 'Engineer',
                'address': {'street': '123 Test St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@test.com',
                'phone': '0412345678',
                'relationship_status': 'single'
            },
            'has_children': False,
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Executor', 'relationship': 'friend', 'address': {'street': '456 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'beneficiaries': [
                {'id': 'ben_1', 'type': 'individual', 'full_name': 'Beneficiary', 'relationship': 'sibling',
                 'address': {'street': '789 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                 'gift_role': 'residue', 'residue_share_percent': 100.0}
            ],
            'distribution': {'scheme': 'custom_structured'},
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'minor_trusts': {'enabled': False},
            'funeral': {'enabled': False},
            'digital_assets': {'enabled': False},
            'pets': {'enabled': False},
            'business': {'enabled': False},
            'exclusions': {'enabled': False},
            'life_sustaining': {'enabled': False},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        
        result = validate_payload(payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(payload)
        summary = generate_will_summary(context)
        
        # Should have warning about no backup executors
        backup_warnings = [w for w in summary.warnings if 'Backup' in w.title or 'backup' in w.message.lower()]
        self.assertTrue(len(backup_warnings) > 0)


class TestClauseExplainability(unittest.TestCase):
    """Test clause explainability generation."""
    
    def test_clause_explainability_structure(self):
        """Test that clause explainability has correct structure."""
        payload = {
            'eligibility': {'confirm_age_over_18': True, 'confirm_qld': True, 'confirm_not_legal_advice': True},
            'will_maker': {
                'full_name': 'Test',
                'dob': '1970-01-15',
                'occupation': 'Engineer',
                'address': {'street': '123 Test St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@test.com',
                'phone': '0412345678',
                'relationship_status': 'single'
            },
            'has_children': False,
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Executor', 'relationship': 'friend', 'address': {'street': '456 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'beneficiaries': [
                {'id': 'ben_1', 'type': 'individual', 'full_name': 'Beneficiary', 'relationship': 'sibling',
                 'address': {'street': '789 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                 'gift_role': 'residue', 'residue_share_percent': 100.0}
            ],
            'distribution': {'scheme': 'custom_structured'},
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'minor_trusts': {'enabled': False},
            'funeral': {'enabled': False},
            'digital_assets': {'enabled': False},
            'pets': {'enabled': False},
            'business': {'enabled': False},
            'exclusions': {'enabled': False},
            'life_sustaining': {'enabled': False},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        
        result = validate_payload(payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(payload)
        clause_explain = generate_clause_explainability(context)
        
        self.assertIn('total_clauses', clause_explain)
        self.assertIn('clauses', clause_explain)
        self.assertTrue(clause_explain['total_clauses'] > 0)
        self.assertEqual(len(clause_explain['clauses']), clause_explain['total_clauses'])
        
        # Check each clause has required fields
        for clause in clause_explain['clauses']:
            self.assertIn('number', clause)
            self.assertIn('clause_id', clause)
            self.assertIn('title', clause)
            self.assertIn('purpose', clause)
            self.assertIn('when_applies', clause)
            self.assertIn('key_points', clause)
            self.assertIsInstance(clause['key_points'], list)


class TestExecutionChecklistSummary(unittest.TestCase):
    """Test execution checklist summary generation."""
    
    def test_execution_summary_structure(self):
        """Test that execution summary has correct structure."""
        payload = {
            'eligibility': {'confirm_age_over_18': True, 'confirm_qld': True, 'confirm_not_legal_advice': True},
            'will_maker': {
                'full_name': 'Test Person',
                'dob': '1970-01-15',
                'occupation': 'Engineer',
                'address': {'street': '123 Test St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                'email': 'test@test.com',
                'phone': '0412345678',
                'relationship_status': 'single'
            },
            'has_children': False,
            'dependants': {'has_other_dependants': False},
            'executors': {
                'mode': 'one',
                'primary': [{'full_name': 'Executor', 'relationship': 'friend', 'address': {'street': '456 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'}}],
                'backup': {'mode': 'none'}
            },
            'beneficiaries': [
                {'id': 'ben_1', 'type': 'individual', 'full_name': 'Beneficiary', 'relationship': 'sibling',
                 'address': {'street': '789 St', 'suburb': 'Brisbane', 'state': 'QLD', 'postcode': '4000'},
                 'gift_role': 'residue', 'residue_share_percent': 100.0}
            ],
            'distribution': {'scheme': 'custom_structured'},
            'survivorship': {'days': 30},
            'substitution': {'rule': 'to_their_children'},
            'minor_trusts': {'enabled': False},
            'funeral': {'enabled': False},
            'digital_assets': {'enabled': False},
            'pets': {'enabled': False},
            'business': {'enabled': False},
            'exclusions': {'enabled': False},
            'life_sustaining': {'enabled': False},
            'declarations': {
                'confirm_reviewed': True,
                'confirm_complex_advice': True,
                'confirm_super_and_joint': True,
                'confirm_signing_witness': True
            }
        }
        
        result = validate_payload(payload)
        self.assertTrue(result.is_valid)
        
        context = build_context(payload)
        summary = generate_execution_checklist_summary(context)
        
        self.assertIn('signing_requirements', summary)
        self.assertIn('who_cannot_witness', summary)
        self.assertIn('storage_recommendations', summary)
        self.assertIn('next_steps', summary)
        
        # Check signing requirements
        signing = summary['signing_requirements']
        self.assertIn('must_be_signed_by', signing)
        self.assertIn('number_of_witnesses', signing)
        self.assertIn('witness_requirements', signing)
        self.assertEqual(signing['number_of_witnesses'], 2)


if __name__ == '__main__':
    unittest.main()
