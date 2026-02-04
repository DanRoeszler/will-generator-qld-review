"""
Unit tests for clause logic module.
"""

import pytest
from app.clause_logic import (
    select_clauses, get_clause_title, get_clause_number,
    get_clause_description, validate_clause_order,
    CLAUSE_TITLE_IDENTIFICATION, CLAUSE_REVOCATION, CLAUSE_DEFINITIONS,
    CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES, CLAUSE_FUNERAL_WISHES,
    CLAUSE_GUARDIANSHIP, CLAUSE_DISTRIBUTION_OVERVIEW, CLAUSE_SPECIFIC_GIFTS,
    CLAUSE_RESIDUE_DISTRIBUTION, CLAUSE_SURVIVORSHIP, CLAUSE_SUBSTITUTION,
    CLAUSE_MINOR_TRUSTS, CLAUSE_ADMINISTRATIVE_POWERS, CLAUSE_DIGITAL_ASSETS,
    CLAUSE_PETS, CLAUSE_BUSINESS_INTERESTS, CLAUSE_EXCLUSION_NOTE,
    CLAUSE_LIFE_SUSTAINING_STATEMENT, CLAUSE_ATTESTATION
)
from app.context_builder import WillContext, WillMaker, Address


class TestClauseSelection:
    def test_always_included_clauses(self):
        """Test that certain clauses always appear."""
        context = WillContext()
        context.will_maker = WillMaker(full_name='Test Person')
        
        clauses = select_clauses(context)
        
        assert CLAUSE_TITLE_IDENTIFICATION in clauses
        assert CLAUSE_REVOCATION in clauses
        assert CLAUSE_DEFINITIONS in clauses
        assert CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES in clauses
        assert CLAUSE_RESIDUE_DISTRIBUTION in clauses
        assert CLAUSE_SURVIVORSHIP in clauses
        assert CLAUSE_ADMINISTRATIVE_POWERS in clauses
        assert CLAUSE_ATTESTATION in clauses

    def test_funeral_wishes_conditional(self):
        """Test that funeral wishes only appears when enabled."""
        context = WillContext()
        context.has_funeral_wishes = False
        
        clauses = select_clauses(context)
        assert CLAUSE_FUNERAL_WISHES not in clauses
        
        context.has_funeral_wishes = True
        clauses = select_clauses(context)
        assert CLAUSE_FUNERAL_WISHES in clauses

    def test_guardianship_conditional(self):
        """Test that guardianship only appears when applicable."""
        context = WillContext()
        context.has_guardianship = False
        
        clauses = select_clauses(context)
        assert CLAUSE_GUARDIANSHIP not in clauses
        
        context.has_guardianship = True
        clauses = select_clauses(context)
        assert CLAUSE_GUARDIANSHIP in clauses

    def test_specific_gifts_conditional(self):
        """Test that specific gifts only appears when there are gifts."""
        context = WillContext()
        context.has_specific_gifts = False
        
        clauses = select_clauses(context)
        assert CLAUSE_SPECIFIC_GIFTS not in clauses
        
        context.has_specific_gifts = True
        clauses = select_clauses(context)
        assert CLAUSE_SPECIFIC_GIFTS in clauses

    def test_substitution_conditional(self):
        """Test that substitution only appears when configured."""
        context = WillContext()
        context.has_substitution = False
        
        clauses = select_clauses(context)
        assert CLAUSE_SUBSTITUTION not in clauses
        
        context.has_substitution = True
        clauses = select_clauses(context)
        assert CLAUSE_SUBSTITUTION in clauses

    def test_minor_trusts_conditional(self):
        """Test that minor trusts only appears when applicable."""
        context = WillContext()
        context.has_minor_trusts = False
        
        clauses = select_clauses(context)
        assert CLAUSE_MINOR_TRUSTS not in clauses
        
        context.has_minor_trusts = True
        clauses = select_clauses(context)
        assert CLAUSE_MINOR_TRUSTS in clauses

    def test_digital_assets_conditional(self):
        """Test that digital assets only appears when enabled."""
        context = WillContext()
        context.has_digital_assets = False
        
        clauses = select_clauses(context)
        assert CLAUSE_DIGITAL_ASSETS not in clauses
        
        context.has_digital_assets = True
        clauses = select_clauses(context)
        assert CLAUSE_DIGITAL_ASSETS in clauses

    def test_pets_conditional(self):
        """Test that pets clause only appears when enabled."""
        context = WillContext()
        context.has_pets = False
        
        clauses = select_clauses(context)
        assert CLAUSE_PETS not in clauses
        
        context.has_pets = True
        clauses = select_clauses(context)
        assert CLAUSE_PETS in clauses

    def test_business_interests_conditional(self):
        """Test that business interests only appears when enabled."""
        context = WillContext()
        context.has_business_interests = False
        
        clauses = select_clauses(context)
        assert CLAUSE_BUSINESS_INTERESTS not in clauses
        
        context.has_business_interests = True
        clauses = select_clauses(context)
        assert CLAUSE_BUSINESS_INTERESTS in clauses

    def test_exclusion_conditional(self):
        """Test that exclusion note only appears when enabled."""
        context = WillContext()
        context.has_exclusions = False
        
        clauses = select_clauses(context)
        assert CLAUSE_EXCLUSION_NOTE not in clauses
        
        context.has_exclusions = True
        clauses = select_clauses(context)
        assert CLAUSE_EXCLUSION_NOTE in clauses

    def test_life_sustaining_conditional(self):
        """Test that life sustaining statement only appears when enabled."""
        context = WillContext()
        context.has_life_sustaining_statement = False
        
        clauses = select_clauses(context)
        assert CLAUSE_LIFE_SUSTAINING_STATEMENT not in clauses
        
        context.has_life_sustaining_statement = True
        clauses = select_clauses(context)
        assert CLAUSE_LIFE_SUSTAINING_STATEMENT in clauses

    def test_no_duplicate_clauses(self):
        """Test that no clause appears more than once."""
        context = WillContext()
        context.has_funeral_wishes = True
        context.has_guardianship = True
        context.has_specific_gifts = True
        context.has_substitution = True
        context.has_minor_trusts = True
        context.has_digital_assets = True
        context.has_pets = True
        context.has_business_interests = True
        context.has_exclusions = True
        context.has_life_sustaining_statement = True
        
        clauses = select_clauses(context)
        
        # Check no duplicates
        assert len(clauses) == len(set(clauses))

    def test_clause_order_consistency(self):
        """Test that clause order is consistent."""
        context = WillContext()
        context.has_funeral_wishes = True
        context.has_guardianship = True
        context.has_specific_gifts = True
        
        clauses1 = select_clauses(context)
        clauses2 = select_clauses(context)
        
        assert clauses1 == clauses2


class TestClauseOrder:
    def test_order_is_valid(self):
        """Test that selected clauses follow the defined order."""
        context = WillContext()
        context.has_funeral_wishes = True
        context.has_guardianship = True
        context.has_specific_gifts = True
        context.has_substitution = True
        context.has_minor_trusts = True
        context.has_digital_assets = True
        context.has_pets = True
        context.has_business_interests = True
        context.has_exclusions = True
        context.has_life_sustaining_statement = True
        
        clauses = select_clauses(context)
        
        assert validate_clause_order(clauses) is True

    def test_title_always_first(self):
        """Test that title clause is always first."""
        context = WillContext()
        clauses = select_clauses(context)
        
        assert clauses[0] == CLAUSE_TITLE_IDENTIFICATION

    def test_attestation_always_last(self):
        """Test that attestation clause is always last."""
        context = WillContext()
        clauses = select_clauses(context)
        
        assert clauses[-1] == CLAUSE_ATTESTATION


class TestClauseTitles:
    def test_all_clauses_have_titles(self):
        """Test that all clause IDs have corresponding titles."""
        all_clauses = [
            CLAUSE_TITLE_IDENTIFICATION,
            CLAUSE_REVOCATION,
            CLAUSE_DEFINITIONS,
            CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES,
            CLAUSE_FUNERAL_WISHES,
            CLAUSE_GUARDIANSHIP,
            CLAUSE_DISTRIBUTION_OVERVIEW,
            CLAUSE_SPECIFIC_GIFTS,
            CLAUSE_RESIDUE_DISTRIBUTION,
            CLAUSE_SURVIVORSHIP,
            CLAUSE_SUBSTITUTION,
            CLAUSE_MINOR_TRUSTS,
            CLAUSE_ADMINISTRATIVE_POWERS,
            CLAUSE_DIGITAL_ASSETS,
            CLAUSE_PETS,
            CLAUSE_BUSINESS_INTERESTS,
            CLAUSE_EXCLUSION_NOTE,
            CLAUSE_LIFE_SUSTAINING_STATEMENT,
            CLAUSE_ATTESTATION,
        ]
        
        for clause_id in all_clauses:
            title = get_clause_title(clause_id)
            assert title is not None
            assert len(title) > 0
            assert clause_id not in title  # Title should be human-readable

    def test_clause_numbering(self):
        """Test that clause numbering works correctly."""
        selected = [
            CLAUSE_TITLE_IDENTIFICATION,
            CLAUSE_REVOCATION,
            CLAUSE_DEFINITIONS,
        ]
        
        assert get_clause_number(CLAUSE_TITLE_IDENTIFICATION, selected) == 1
        assert get_clause_number(CLAUSE_REVOCATION, selected) == 2
        assert get_clause_number(CLAUSE_DEFINITIONS, selected) == 3
        assert get_clause_number(CLAUSE_GUARDIANSHIP, selected) == 0  # Not in list


class TestClauseDescriptions:
    def test_all_clauses_have_descriptions(self):
        """Test that all clause IDs have corresponding descriptions."""
        all_clauses = [
            CLAUSE_TITLE_IDENTIFICATION,
            CLAUSE_REVOCATION,
            CLAUSE_DEFINITIONS,
            CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES,
            CLAUSE_FUNERAL_WISHES,
            CLAUSE_GUARDIANSHIP,
            CLAUSE_DISTRIBUTION_OVERVIEW,
            CLAUSE_SPECIFIC_GIFTS,
            CLAUSE_RESIDUE_DISTRIBUTION,
            CLAUSE_SURVIVORSHIP,
            CLAUSE_SUBSTITUTION,
            CLAUSE_MINOR_TRUSTS,
            CLAUSE_ADMINISTRATIVE_POWERS,
            CLAUSE_DIGITAL_ASSETS,
            CLAUSE_PETS,
            CLAUSE_BUSINESS_INTERESTS,
            CLAUSE_EXCLUSION_NOTE,
            CLAUSE_LIFE_SUSTAINING_STATEMENT,
            CLAUSE_ATTESTATION,
        ]
        
        for clause_id in all_clauses:
            description = get_clause_description(clause_id)
            assert description is not None
            assert len(description) > 0


class TestComplexScenarios:
    def test_full_will_clauses(self):
        """Test clause selection for a full will with all options."""
        context = WillContext()
        context.will_maker = WillMaker(full_name='Test Person')
        context.has_partner = True
        context.has_children = True
        context.has_minor_children = True
        context.has_guardianship = True
        context.has_specific_gifts = True
        context.has_residue_scheme = True
        context.has_percentages = True
        context.has_substitution = True
        context.has_minor_trusts = True
        context.has_digital_assets = True
        context.has_pets = True
        context.has_business_interests = True
        context.has_exclusions = True
        context.has_life_sustaining_statement = True
        context.has_funeral_wishes = True
        
        clauses = select_clauses(context)
        
        # Should have all clauses
        assert len(clauses) == 19
        
        # Verify order
        expected_order = [
            CLAUSE_TITLE_IDENTIFICATION,
            CLAUSE_REVOCATION,
            CLAUSE_DEFINITIONS,
            CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES,
            CLAUSE_FUNERAL_WISHES,
            CLAUSE_GUARDIANSHIP,
            CLAUSE_DISTRIBUTION_OVERVIEW,
            CLAUSE_SPECIFIC_GIFTS,
            CLAUSE_RESIDUE_DISTRIBUTION,
            CLAUSE_SURVIVORSHIP,
            CLAUSE_SUBSTITUTION,
            CLAUSE_MINOR_TRUSTS,
            CLAUSE_ADMINISTRATIVE_POWERS,
            CLAUSE_DIGITAL_ASSETS,
            CLAUSE_PETS,
            CLAUSE_BUSINESS_INTERESTS,
            CLAUSE_EXCLUSION_NOTE,
            CLAUSE_LIFE_SUSTAINING_STATEMENT,
            CLAUSE_ATTESTATION,
        ]
        
        assert clauses == expected_order

    def test_simple_will_clauses(self):
        """Test clause selection for a simple will with minimal options."""
        context = WillContext()
        context.will_maker = WillMaker(full_name='Test Person')
        context.has_partner = False
        context.has_children = False
        context.has_minor_children = False
        context.has_guardianship = False
        context.has_specific_gifts = False
        context.has_substitution = False
        context.has_minor_trusts = False
        context.has_digital_assets = False
        context.has_pets = False
        context.has_business_interests = False
        context.has_exclusions = False
        context.has_life_sustaining_statement = False
        context.has_funeral_wishes = False
        
        clauses = select_clauses(context)
        
        # Should only have required clauses
        assert CLAUSE_TITLE_IDENTIFICATION in clauses
        assert CLAUSE_REVOCATION in clauses
        assert CLAUSE_DEFINITIONS in clauses
        assert CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES in clauses
        assert CLAUSE_RESIDUE_DISTRIBUTION in clauses
        assert CLAUSE_SURVIVORSHIP in clauses
        assert CLAUSE_ADMINISTRATIVE_POWERS in clauses
        assert CLAUSE_ATTESTATION in clauses
        
        # Should not have optional clauses
        assert CLAUSE_FUNERAL_WISHES not in clauses
        assert CLAUSE_GUARDIANSHIP not in clauses
        assert CLAUSE_SPECIFIC_GIFTS not in clauses
        assert CLAUSE_SUBSTITUTION not in clauses
        assert CLAUSE_MINOR_TRUSTS not in clauses
        assert CLAUSE_DIGITAL_ASSETS not in clauses
        assert CLAUSE_PETS not in clauses
        assert CLAUSE_BUSINESS_INTERESTS not in clauses
        assert CLAUSE_EXCLUSION_NOTE not in clauses
        assert CLAUSE_LIFE_SUSTAINING_STATEMENT not in clauses


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
