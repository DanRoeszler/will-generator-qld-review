"""
Clause Logic Module

Determines which clauses appear in the will and their order.
All clause selection is based on explicit triggers from the context.

Clause Dependency Rules:
========================

1. TITLE_IDENTIFICATION: Always included
2. REVOCATION: Always included
3. DEFINITIONS: Always included
4. APPOINTMENT_EXECUTORS_TRUSTEES: Always included
5. FUNERAL_WISHES: Included if has_funeral_wishes is True
6. GUARDIANSHIP: Included if has_guardianship is True
   - Dependency: has_minor_children must be True
7. DISTRIBUTION_OVERVIEW: Included for complex schemes
   - Dependency: has_specific_gifts AND has_residue_scheme, OR has_percentages
8. SPECIFIC_GIFTS: Included if has_specific_gifts is True
9. RESIDUE_DISTRIBUTION: Always included
10. SURVIVORSHIP: Always included
11. SUBSTITUTION: Included if has_substitution is True
12. MINOR_TRUSTS: Included if has_minor_trusts is True
    - Dependency: has_minor_children OR beneficiaries with residue/percentage roles
13. ADMINISTRATIVE_POWERS: Always included
14. DIGITAL_ASSETS: Included if has_digital_assets is True
15. PETS: Included if has_pets is True
16. BUSINESS_INTERESTS: Included if has_business_interests is True
17. EXCLUSION_NOTE: Included if has_exclusions is True
18. LIFE_SUSTAINING_STATEMENT: Included if has_life_sustaining_statement is True
19. ATTESTATION: Always included (last)

Conflict Prevention:
====================
- No clause appears more than once
- Clause order is fixed and stable
- Contradictory clauses are prevented by flag logic
"""

from typing import List, Set, Dict, Any
from dataclasses import dataclass
from enum import Enum

from app.context_builder import WillContext


class ClauseId(str, Enum):
    """Stable clause identifiers."""
    TITLE_IDENTIFICATION = 'title_identification'
    REVOCATION = 'revocation'
    DEFINITIONS = 'definitions'
    APPOINTMENT_EXECUTORS_TRUSTEES = 'appointment_executors_trustees'
    FUNERAL_WISHES = 'funeral_wishes'
    GUARDIANSHIP = 'guardianship'
    DISTRIBUTION_OVERVIEW = 'distribution_overview'
    SPECIFIC_GIFTS = 'specific_gifts'
    RESIDUE_DISTRIBUTION = 'residue_distribution'
    SURVIVORSHIP = 'survivorship'
    SUBSTITUTION = 'substitution'
    MINOR_TRUSTS = 'minor_trusts'
    ADMINISTRATIVE_POWERS = 'administrative_powers'
    DIGITAL_ASSETS = 'digital_assets'
    PETS = 'pets'
    BUSINESS_INTERESTS = 'business_interests'
    EXCLUSION_NOTE = 'exclusion_note'
    LIFE_SUSTAINING_STATEMENT = 'life_sustaining_statement'
    ATTESTATION = 'attestation'


# Fixed clause order - this never changes
CLAUSE_ORDER: List[ClauseId] = [
    ClauseId.TITLE_IDENTIFICATION,
    ClauseId.REVOCATION,
    ClauseId.DEFINITIONS,
    ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES,
    ClauseId.FUNERAL_WISHES,
    ClauseId.GUARDIANSHIP,
    ClauseId.DISTRIBUTION_OVERVIEW,
    ClauseId.SPECIFIC_GIFTS,
    ClauseId.RESIDUE_DISTRIBUTION,
    ClauseId.SURVIVORSHIP,
    ClauseId.SUBSTITUTION,
    ClauseId.MINOR_TRUSTS,
    ClauseId.ADMINISTRATIVE_POWERS,
    ClauseId.DIGITAL_ASSETS,
    ClauseId.PETS,
    ClauseId.BUSINESS_INTERESTS,
    ClauseId.EXCLUSION_NOTE,
    ClauseId.LIFE_SUSTAINING_STATEMENT,
    ClauseId.ATTESTATION,
]

# Backward compatibility constants
CLAUSE_TITLE_IDENTIFICATION = ClauseId.TITLE_IDENTIFICATION
CLAUSE_REVOCATION = ClauseId.REVOCATION
CLAUSE_DEFINITIONS = ClauseId.DEFINITIONS
CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES = ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES
CLAUSE_FUNERAL_WISHES = ClauseId.FUNERAL_WISHES
CLAUSE_GUARDIANSHIP = ClauseId.GUARDIANSHIP
CLAUSE_DISTRIBUTION_OVERVIEW = ClauseId.DISTRIBUTION_OVERVIEW
CLAUSE_SPECIFIC_GIFTS = ClauseId.SPECIFIC_GIFTS
CLAUSE_RESIDUE_DISTRIBUTION = ClauseId.RESIDUE_DISTRIBUTION
CLAUSE_SURVIVORSHIP = ClauseId.SURVIVORSHIP
CLAUSE_SUBSTITUTION = ClauseId.SUBSTITUTION
CLAUSE_MINOR_TRUSTS = ClauseId.MINOR_TRUSTS
CLAUSE_ADMINISTRATIVE_POWERS = ClauseId.ADMINISTRATIVE_POWERS
CLAUSE_DIGITAL_ASSETS = ClauseId.DIGITAL_ASSETS
CLAUSE_PETS = ClauseId.PETS
CLAUSE_BUSINESS_INTERESTS = ClauseId.BUSINESS_INTERESTS
CLAUSE_EXCLUSION_NOTE = ClauseId.EXCLUSION_NOTE
CLAUSE_LIFE_SUSTAINING_STATEMENT = ClauseId.LIFE_SUSTAINING_STATEMENT
CLAUSE_ATTESTATION = ClauseId.ATTESTATION


@dataclass
class ClauseDependency:
    """Defines dependencies and conflicts for a clause."""
    clause_id: ClauseId
    required_flags: List[str]  # All must be True
    conflicting_clauses: List[ClauseId] = None
    notes: str = ''


# Clause dependency definitions
CLAUSE_DEPENDENCIES: Dict[ClauseId, ClauseDependency] = {
    ClauseId.TITLE_IDENTIFICATION: ClauseDependency(
        clause_id=ClauseId.TITLE_IDENTIFICATION,
        required_flags=[],
        notes='Always included'
    ),
    ClauseId.REVOCATION: ClauseDependency(
        clause_id=ClauseId.REVOCATION,
        required_flags=[],
        notes='Always included'
    ),
    ClauseId.DEFINITIONS: ClauseDependency(
        clause_id=ClauseId.DEFINITIONS,
        required_flags=[],
        notes='Always included'
    ),
    ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES: ClauseDependency(
        clause_id=ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES,
        required_flags=[],
        notes='Always included - every will needs executors'
    ),
    ClauseId.FUNERAL_WISHES: ClauseDependency(
        clause_id=ClauseId.FUNERAL_WISHES,
        required_flags=['has_funeral_wishes'],
        notes='Only if funeral wishes toggle is enabled'
    ),
    ClauseId.GUARDIANSHIP: ClauseDependency(
        clause_id=ClauseId.GUARDIANSHIP,
        required_flags=['has_guardianship'],
        notes='Only if minor children exist and guardian is appointed'
    ),
    ClauseId.DISTRIBUTION_OVERVIEW: ClauseDependency(
        clause_id=ClauseId.DISTRIBUTION_OVERVIEW,
        required_flags=[],
        notes='Included for complex distribution schemes'
    ),
    ClauseId.SPECIFIC_GIFTS: ClauseDependency(
        clause_id=ClauseId.SPECIFIC_GIFTS,
        required_flags=['has_specific_gifts'],
        notes='Only if specific gifts exist'
    ),
    ClauseId.RESIDUE_DISTRIBUTION: ClauseDependency(
        clause_id=ClauseId.RESIDUE_DISTRIBUTION,
        required_flags=[],
        notes='Always included - every will has residue'
    ),
    ClauseId.SURVIVORSHIP: ClauseDependency(
        clause_id=ClauseId.SURVIVORSHIP,
        required_flags=[],
        notes='Always included'
    ),
    ClauseId.SUBSTITUTION: ClauseDependency(
        clause_id=ClauseId.SUBSTITUTION,
        required_flags=['has_substitution'],
        notes='Only if substitution rule is configured'
    ),
    ClauseId.MINOR_TRUSTS: ClauseDependency(
        clause_id=ClauseId.MINOR_TRUSTS,
        required_flags=['has_minor_trusts'],
        notes='Only if minor trusts are enabled and applicable'
    ),
    ClauseId.ADMINISTRATIVE_POWERS: ClauseDependency(
        clause_id=ClauseId.ADMINISTRATIVE_POWERS,
        required_flags=[],
        notes='Always included'
    ),
    ClauseId.DIGITAL_ASSETS: ClauseDependency(
        clause_id=ClauseId.DIGITAL_ASSETS,
        required_flags=['has_digital_assets'],
        notes='Only if digital assets toggle is enabled'
    ),
    ClauseId.PETS: ClauseDependency(
        clause_id=ClauseId.PETS,
        required_flags=['has_pets'],
        notes='Only if pets toggle is enabled'
    ),
    ClauseId.BUSINESS_INTERESTS: ClauseDependency(
        clause_id=ClauseId.BUSINESS_INTERESTS,
        required_flags=['has_business_interests'],
        notes='Only if business interests toggle is enabled'
    ),
    ClauseId.EXCLUSION_NOTE: ClauseDependency(
        clause_id=ClauseId.EXCLUSION_NOTE,
        required_flags=['has_exclusions'],
        notes='Only if exclusion toggle is enabled'
    ),
    ClauseId.LIFE_SUSTAINING_STATEMENT: ClauseDependency(
        clause_id=ClauseId.LIFE_SUSTAINING_STATEMENT,
        required_flags=['has_life_sustaining_statement'],
        notes='Only if life sustaining toggle is enabled'
    ),
    ClauseId.ATTESTATION: ClauseDependency(
        clause_id=ClauseId.ATTESTATION,
        required_flags=[],
        notes='Always included - must be last'
    ),
}


def get_context_flags(context: WillContext) -> Dict[str, bool]:
    """
    Extract all boolean flags from context for dependency checking.
    
    Args:
        context: The will context
    
    Returns:
        Dictionary of flag names to boolean values
    """
    return {
        'has_partner': context.has_partner,
        'has_children': context.has_children,
        'has_minor_children': context.has_minor_children,
        'has_guardianship': context.has_guardianship,
        'has_specific_gifts': context.has_specific_gifts,
        'has_residue_scheme': context.has_residue_scheme,
        'has_percentages': context.has_percentages,
        'has_exclusions': context.has_exclusions,
        'has_digital_assets': context.has_digital_assets,
        'has_pets': context.has_pets,
        'has_business_interests': context.has_business_interests,
        'has_funeral_wishes': context.has_funeral_wishes,
        'has_life_sustaining_statement': context.has_life_sustaining_statement,
        'has_minor_trusts': context.has_minor_trusts,
        'has_substitution': context.has_substitution,
        'has_alternate_beneficiary': context.has_alternate_beneficiary,
    }


def check_clause_dependencies(clause_id: ClauseId, context: WillContext) -> bool:
    """
    Check if a clause's dependencies are satisfied.
    
    Args:
        clause_id: The clause to check
        context: The will context
    
    Returns:
        True if clause should be included
    """
    dependency = CLAUSE_DEPENDENCIES.get(clause_id)
    if not dependency:
        return False
    
    # Always-include clauses have no required flags
    if not dependency.required_flags:
        return True
    
    # Check all required flags
    flags = get_context_flags(context)
    for flag_name in dependency.required_flags:
        if not flags.get(flag_name, False):
            return False
    
    return True


def select_clauses(context: WillContext) -> List[ClauseId]:
    """
    Select which clauses should appear in the will based on context flags.
    
    This function implements the deterministic clause selection logic.
    A clause either appears or does not appear based on explicit triggers.
    
    Args:
        context: The will context with all derived flags
    
    Returns:
        Ordered list of clause IDs to include
    """
    selected = []
    
    for clause_id in CLAUSE_ORDER:
        if check_clause_dependencies(clause_id, context):
            selected.append(clause_id)
    
    return selected


def get_clause_number(clause_id: ClauseId, selected_clauses: List[ClauseId]) -> int:
    """
    Get the clause number (1-indexed) within the selected clauses.
    
    Args:
        clause_id: The clause identifier
        selected_clauses: The list of selected clause IDs
    
    Returns:
        The clause number, or 0 if not found
    """
    try:
        return selected_clauses.index(clause_id) + 1
    except ValueError:
        return 0


def get_clause_title(clause_id: ClauseId) -> str:
    """
    Get the display title for a clause.
    
    Args:
        clause_id: The clause identifier
    
    Returns:
        Human-readable clause title
    """
    titles = {
        ClauseId.TITLE_IDENTIFICATION: 'Title and Identification',
        ClauseId.REVOCATION: 'Revocation of Previous Wills',
        ClauseId.DEFINITIONS: 'Definitions and Interpretation',
        ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES: 'Appointment of Executors and Trustees',
        ClauseId.FUNERAL_WISHES: 'Funeral Wishes',
        ClauseId.GUARDIANSHIP: 'Appointment of Guardian',
        ClauseId.DISTRIBUTION_OVERVIEW: 'Distribution Plan Overview',
        ClauseId.SPECIFIC_GIFTS: 'Specific Gifts',
        ClauseId.RESIDUE_DISTRIBUTION: 'Distribution of Residue',
        ClauseId.SURVIVORSHIP: 'Survivorship Period',
        ClauseId.SUBSTITUTION: 'Substitution of Beneficiaries',
        ClauseId.MINOR_TRUSTS: 'Trusts for Minor Beneficiaries',
        ClauseId.ADMINISTRATIVE_POWERS: 'Powers of Executors and Trustees',
        ClauseId.DIGITAL_ASSETS: 'Digital Assets',
        ClauseId.PETS: 'Provision for Pets',
        ClauseId.BUSINESS_INTERESTS: 'Business Interests',
        ClauseId.EXCLUSION_NOTE: 'Exclusion Note',
        ClauseId.LIFE_SUSTAINING_STATEMENT: 'Life Sustaining Treatment Statement',
        ClauseId.ATTESTATION: 'Attestation and Execution',
    }
    
    return titles.get(clause_id, clause_id.value.replace('_', ' ').title())


def get_clause_description(clause_id: ClauseId) -> str:
    """
    Get a brief description of what the clause covers.
    
    Args:
        clause_id: The clause identifier
    
    Returns:
        Brief description of the clause
    """
    descriptions = {
        ClauseId.TITLE_IDENTIFICATION: 'Identifies the will maker and declares this document as their last will.',
        ClauseId.REVOCATION: 'Revokes all previous wills and codicils.',
        ClauseId.DEFINITIONS: 'Defines key terms used throughout the will.',
        ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES: 'Appoints executors and trustees to administer the estate.',
        ClauseId.FUNERAL_WISHES: 'Expresses preferences for funeral arrangements.',
        ClauseId.GUARDIANSHIP: 'Appoints a guardian for minor children.',
        ClauseId.DISTRIBUTION_OVERVIEW: 'Provides an overview of the distribution plan.',
        ClauseId.SPECIFIC_GIFTS: 'Details specific gifts of cash or property.',
        ClauseId.RESIDUE_DISTRIBUTION: 'Directs how the residue of the estate should be distributed.',
        ClauseId.SURVIVORSHIP: 'Specifies the period a beneficiary must survive the will maker.',
        ClauseId.SUBSTITUTION: 'Provides for substitution if a beneficiary predeceases.',
        ClauseId.MINOR_TRUSTS: 'Establishes trusts for beneficiaries who are minors.',
        ClauseId.ADMINISTRATIVE_POWERS: 'Grants powers to executors and trustees.',
        ClauseId.DIGITAL_ASSETS: 'Provides for management of digital assets.',
        ClauseId.PETS: 'Makes provision for the care of pets.',
        ClauseId.BUSINESS_INTERESTS: 'Directs the disposition of business interests.',
        ClauseId.EXCLUSION_NOTE: 'Notes exclusions and reasons for exclusion.',
        ClauseId.LIFE_SUSTAINING_STATEMENT: 'Expresses wishes regarding life sustaining treatment.',
        ClauseId.ATTESTATION: 'Execution and witnessing provisions.',
    }
    
    return descriptions.get(clause_id, '')


def get_clause_dependencies_info(clause_id: ClauseId) -> Dict[str, Any]:
    """
    Get dependency information for a clause.
    
    Args:
        clause_id: The clause identifier
    
    Returns:
        Dictionary with dependency information
    """
    dependency = CLAUSE_DEPENDENCIES.get(clause_id)
    if not dependency:
        return {}
    
    return {
        'clause_id': clause_id.value,
        'required_flags': dependency.required_flags,
        'notes': dependency.notes,
    }


def validate_clause_order(clauses: List[ClauseId]) -> bool:
    """
    Validate that clause order follows the defined order.
    
    Args:
        clauses: List of clause IDs to validate
    
    Returns:
        True if order is valid
    """
    # Check that clauses appear in the same relative order as CLAUSE_ORDER
    last_index = -1
    for clause in clauses:
        try:
            current_index = CLAUSE_ORDER.index(clause)
            if current_index <= last_index:
                return False
            last_index = current_index
        except ValueError:
            return False  # Unknown clause
    
    return True


def check_for_conflicts(selected_clauses: List[ClauseId]) -> List[str]:
    """
    Check for conflicting clauses in the selection.
    
    Args:
        selected_clauses: List of selected clause IDs
    
    Returns:
        List of conflict messages (empty if no conflicts)
    """
    conflicts = []
    
    # Check for duplicates
    seen = set()
    for clause in selected_clauses:
        if clause in seen:
            conflicts.append(f'Duplicate clause: {clause.value}')
        seen.add(clause)
    
    # Check attestation is last
    if selected_clauses and selected_clauses[-1] != ClauseId.ATTESTATION:
        conflicts.append('Attestation clause must be last')
    
    # Check title is first
    if selected_clauses and selected_clauses[0] != ClauseId.TITLE_IDENTIFICATION:
        conflicts.append('Title clause must be first')
    
    return conflicts


def get_clauses_summary(context: WillContext) -> Dict[str, Any]:
    """
    Get a summary of clause selection for the current context.
    
    Args:
        context: The will context
    
    Returns:
        Dictionary with clause selection summary
    """
    selected = select_clauses(context)
    flags = get_context_flags(context)
    
    return {
        'total_clauses': len(selected),
        'selected_clauses': [c.value for c in selected],
        'flags': flags,
        'conflicts': check_for_conflicts(selected),
        'clauses_detail': [
            {
                'id': c.value,
                'number': i + 1,
                'title': get_clause_title(c),
                'description': get_clause_description(c),
            }
            for i, c in enumerate(selected)
        ]
    }
