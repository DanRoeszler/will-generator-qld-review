"""
Explainability Module

Generates plain-English summaries of what a will does and does not cover,
along with risk warnings. This module provides transparency without
constituting legal advice.

All summaries are generated deterministically from the will context.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from app.context_builder import WillContext
from app.clause_logic import select_clauses, ClauseId, get_clause_title


class RiskLevel(str, Enum):
    """Risk severity levels for warnings."""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


@dataclass
class WillSummarySection:
    """A section of the will summary."""
    title: str
    content: str
    order: int = 0


@dataclass
class RiskWarning:
    """A risk warning for the will maker."""
    level: RiskLevel
    category: str
    title: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class WhatWillDoesNotCover:
    """Items explicitly not covered by the will."""
    category: str
    description: str
    reason: str


@dataclass
class WillSummary:
    """Complete plain-English summary of a will."""
    # Overview
    will_maker_name: str = ''
    document_type: str = 'Last Will and Testament'
    
    # What the will does
    sections: List[WillSummarySection] = field(default_factory=list)
    
    # What it does not cover
    not_covered: List[WhatWillDoesNotCover] = field(default_factory=list)
    
    # Risk warnings
    warnings: List[RiskWarning] = field(default_factory=list)
    
    # Key facts
    executor_count: int = 0
    beneficiary_count: int = 0
    has_guardian: bool = False
    has_specific_gifts: bool = False
    has_minor_trusts: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary for API response."""
        return {
            'overview': {
                'will_maker_name': self.will_maker_name,
                'document_type': self.document_type,
            },
            'key_facts': {
                'executor_count': self.executor_count,
                'beneficiary_count': self.beneficiary_count,
                'has_guardian': self.has_guardian,
                'has_specific_gifts': self.has_specific_gifts,
                'has_minor_trusts': self.has_minor_trusts,
            },
            'sections': [
                {'title': s.title, 'content': s.content}
                for s in sorted(self.sections, key=lambda x: x.order)
            ],
            'not_covered': [
                {
                    'category': n.category,
                    'description': n.description,
                    'reason': n.reason
                }
                for n in self.not_covered
            ],
            'warnings': [
                {
                    'level': w.level.value,
                    'category': w.category,
                    'title': w.title,
                    'message': w.message,
                    'suggestion': w.suggestion
                }
                for w in self.warnings
            ],
            'warning_counts': {
                'info': len([w for w in self.warnings if w.level == RiskLevel.INFO]),
                'warning': len([w for w in self.warnings if w.level == RiskLevel.WARNING]),
                'critical': len([w for w in self.warnings if w.level == RiskLevel.CRITICAL]),
            }
        }


def generate_will_summary(context: WillContext) -> WillSummary:
    """
    Generate a plain-English summary of what the will does.
    
    Args:
        context: The will context
        
    Returns:
        WillSummary with all sections, warnings, and exclusions
    """
    summary = WillSummary(
        will_maker_name=context.will_maker.full_name,
        executor_count=len(context.executors),
        beneficiary_count=len(context.beneficiaries),
        has_guardian=context.guardian is not None,
        has_specific_gifts=context.has_specific_gifts,
        has_minor_trusts=context.has_minor_trusts,
    )
    
    # Build each summary section
    summary.sections.extend(_build_executor_summary(context))
    summary.sections.extend(_build_distribution_summary(context))
    summary.sections.extend(_build_guardianship_summary(context))
    summary.sections.extend(_build_special_provisions_summary(context))
    
    # Build what the will does NOT cover
    summary.not_covered = _build_not_covered_list(context)
    
    # Generate risk warnings
    summary.warnings = _generate_risk_warnings(context)
    
    return summary


def _build_executor_summary(context: WillContext) -> List[WillSummarySection]:
    """Build summary sections about executors."""
    sections = []
    
    # Primary executors
    if context.executors:
        executor_names = [e.full_name for e in context.executors]
        if len(executor_names) == 1:
            content = (
                f"You have appointed {executor_names[0]} as your executor. "
                f"This person will be responsible for carrying out the instructions in your will, "
                f"including collecting your assets, paying any debts, and distributing your estate "
                f"according to your wishes."
            )
        else:
            names_text = ', '.join(executor_names[:-1]) + ' and ' + executor_names[-1]
            content = (
                f"You have appointed {names_text} as your executors. "
                f"They will work together to carry out the instructions in your will, "
                f"including collecting your assets, paying any debts, and distributing your estate "
                f"according to your wishes."
            )
        
        sections.append(WillSummarySection(
            title='Who Will Manage Your Estate',
            content=content,
            order=1
        ))
    
    # Backup executors
    if context.backup_executors:
        backup_names = [e.full_name for e in context.backup_executors]
        if len(backup_names) == 1:
            content = (
                f"If your primary executor cannot act, {backup_names[0]} will step in as backup executor."
            )
        else:
            names_text = ', '.join(backup_names[:-1]) + ' and ' + backup_names[-1]
            content = (
                f"If your primary executors cannot act, {names_text} will step in as backup executors."
            )
        
        sections.append(WillSummarySection(
            title='Backup Executors',
            content=content,
            order=2
        ))
    
    return sections


def _build_distribution_summary(context: WillContext) -> List[WillSummarySection]:
    """Build summary sections about asset distribution."""
    sections = []
    
    # Specific gifts
    if context.has_specific_gifts and context.specific_gifts:
        gift_descriptions = []
        for gift in context.specific_gifts[:3]:  # Limit to first 3 for summary
            if gift.gift_type == 'cash':
                gift_descriptions.append(
                    f"${gift.cash_amount:,.2f} to {gift.beneficiary_name}"
                )
            else:
                gift_descriptions.append(
                    f"{gift.item_description} to {gift.beneficiary_name}"
                )
        
        if len(context.specific_gifts) > 3:
            gift_descriptions.append(f"and {len(context.specific_gifts) - 3} other specific gifts")
        
        content = (
            f"You have made {len(context.specific_gifts)} specific gift(s): " +
            '; '.join(gift_descriptions) +
            ". These gifts will be distributed first, before the residue of your estate."
        )
        
        sections.append(WillSummarySection(
            title='Specific Gifts',
            content=content,
            order=3
        ))
    
    # Residue distribution
    if context.residue_beneficiaries:
        residue_descriptions = []
        for rb in context.residue_beneficiaries:
            if rb.share_percent:
                residue_descriptions.append(
                    f"{rb.share_percent:.1f}% to {rb.beneficiary_name}"
                )
            else:
                residue_descriptions.append(rb.beneficiary_name)
        
        content = (
            f"After specific gifts and debts are paid, the residue of your estate "
            f"(everything left over) will be distributed as follows: " +
            '; '.join(residue_descriptions) + "."
        )
        
        # Add survivorship info
        if context.survivorship_days > 0:
            content += (
                f" Each beneficiary must survive you by {context.survivorship_days} days "
                f"to receive their share."
            )
        
        sections.append(WillSummarySection(
            title='Distribution of Your Estate',
            content=content,
            order=4
        ))
    
    return sections


def _build_guardianship_summary(context: WillContext) -> List[WillSummarySection]:
    """Build summary sections about guardianship."""
    sections = []
    
    if context.has_guardianship and context.guardian:
        content = (
            f"You have appointed {context.guardian.full_name} as guardian for your minor children. "
            f"This person will have parental responsibility for your children if you pass away "
            f"while they are still minors."
        )
        
        if context.backup_guardian:
            content += (
                f" If {context.guardian.full_name} cannot act, "
                f"{context.backup_guardian.full_name} will step in as backup guardian."
            )
        
        sections.append(WillSummarySection(
            title='Guardianship of Minor Children',
            content=content,
            order=5
        ))
    
    return sections


def _build_special_provisions_summary(context: WillContext) -> List[WillSummarySection]:
    """Build summary sections about special provisions."""
    sections = []
    
    # Minor trusts
    if context.has_minor_trusts:
        content = (
            f"If any beneficiary is under {context.minor_trusts_vesting_age} years old at the time of your death, "
            f"their share will be held in trust until they reach that age. "
        )
        
        if context.minor_trusts_trustee_mode == 'executors':
            content += "Your executors will manage the trust."
        elif context.minor_trusts_trustee_mode == 'separate' and context.minor_trusts_trustee:
            content += f"{context.minor_trusts_trustee.full_name} will manage the trust."
        
        sections.append(WillSummarySection(
            title='Trusts for Young Beneficiaries',
            content=content,
            order=6
        ))
    
    # Funeral wishes
    if context.has_funeral_wishes:
        content = "You have expressed preferences for your funeral arrangements. "
        if context.funeral_preference:
            content += f"You prefer {context.funeral_preference.replace('_', ' ')}. "
        content += "These wishes are not legally binding but provide guidance to your executors."
        
        sections.append(WillSummarySection(
            title='Funeral Wishes',
            content=content,
            order=7
        ))
    
    # Digital assets
    if context.has_digital_assets:
        content = (
            "You have provided for the management of your digital assets (online accounts, "
            "digital files, etc.). Your executors will have authority to access and manage "
            "these assets according to your instructions."
        )
        
        sections.append(WillSummarySection(
            title='Digital Assets',
            content=content,
            order=8
        ))
    
    # Pets
    if context.has_pets:
        content = f"You have made provision for the care of your {context.pets_count} pet(s)."
        if context.pets_carer_name:
            content += f" {context.pets_carer_name} will be responsible for their care."
        if context.pets_cash_gift:
            content += f" A gift of ${context.pets_cash_gift:,.2f} is provided for their expenses."
        
        sections.append(WillSummarySection(
            title='Provision for Pets',
            content=content,
            order=9
        ))
    
    # Business interests
    if context.has_business_interests and context.business_interests:
        business = context.business_interests[0]
        content = (
            f"You have directed how your interest in {business.entity_name} should be handled. "
            f"Your executors will manage this according to your instructions."
        )
        
        sections.append(WillSummarySection(
            title='Business Interests',
            content=content,
            order=10
        ))
    
    # Life sustaining treatment
    if context.has_life_sustaining_statement:
        content = (
            "You have expressed your wishes regarding life-sustaining treatment. "
            "This statement provides guidance to your attorneys if you are unable to make "
            "medical decisions for yourself."
        )
        
        sections.append(WillSummarySection(
            title='Life-Sustaining Treatment',
            content=content,
            order=11
        ))
    
    return sections


def _build_not_covered_list(context: WillContext) -> List[WhatWillDoesNotCover]:
    """Build list of what the will does NOT cover."""
    not_covered = []
    
    # Superannuation
    not_covered.append(WhatWillDoesNotCover(
        category='Superannuation',
        description='Your superannuation benefits are not automatically covered by your will.',
        reason=(
            "Superannuation is held in trust by your super fund and is distributed "
            "according to the fund's rules and any binding death nomination you have made."
        )
    ))
    
    # Life insurance
    not_covered.append(WhatWillDoesNotCover(
        category='Life Insurance',
        description='Life insurance proceeds are paid directly to nominated beneficiaries.',
        reason=(
            "Unless your estate is the nominated beneficiary, life insurance proceeds "
            "bypass your will and go directly to the named beneficiary."
        )
    ))
    
    # Jointly owned property
    not_covered.append(WhatWillDoesNotCover(
        category='Jointly Owned Property',
        description='Property owned as joint tenants passes automatically to the surviving owner.',
        reason=(
            "Property held as 'joint tenants' (common for married couples) passes by "
            "'right of survivorship' and is not part of your estate."
        )
    ))
    
    # Assets in trusts
    not_covered.append(WhatWillDoesNotCover(
        category='Trust Assets',
        description='Assets held in family trusts or other trusts are not covered.',
        reason=(
            "Assets held in trust are owned by the trust, not by you personally. "
            "The trust deed determines how these assets are managed after your death."
        )
    ))
    
    # Company assets
    not_covered.append(WhatWillDoesNotCover(
        category='Company Assets',
        description='Assets owned by companies you control are not your personal assets.',
        reason=(
            "Companies are separate legal entities. The company's assets belong to the "
            "company, not to you personally, even if you own all the shares."
        )
    ))
    
    # Powers of attorney
    not_covered.append(WhatWillDoesNotCover(
        category='Enduring Powers of Attorney',
        description='This will does not create enduring powers of attorney.',
        reason=(
            "Enduring powers of attorney (for financial and personal/health matters) "
            "are separate documents that must be prepared and signed while you have capacity."
        )
    ))
    
    # Advance health directive
    not_covered.append(WhatWillDoesNotCover(
        category='Advance Health Directive',
        description='This will does not create an advance health directive.',
        reason=(
            "An advance health directive is a separate document that provides detailed "
            "instructions about your future health care. It is different from the "
            "life-sustaining statement in your will."
        )
    ))
    
    return not_covered


def _generate_risk_warnings(context: WillContext) -> List[RiskWarning]:
    """Generate risk warnings based on the will configuration."""
    warnings = []
    
    # Check for single executor
    if len(context.executors) == 1:
        warnings.append(RiskWarning(
            level=RiskLevel.INFO,
            category='executors',
            title='Single Executor',
            message='You have appointed only one executor.',
            suggestion='Consider appointing a backup executor in case your primary executor cannot act.'
        ))
    
    # Check for no backup executors
    if len(context.executors) > 0 and len(context.backup_executors) == 0:
        warnings.append(RiskWarning(
            level=RiskLevel.WARNING,
            category='executors',
            title='No Backup Executors',
            message='You have not appointed any backup executors.',
            suggestion=(
                'If your primary executor cannot act (due to death, incapacity, or refusal), '
                'someone may need to apply to the court to administer your estate.'
            )
        ))
    
    # Check for minor children without guardianship
    if context.has_minor_children and not context.has_guardianship:
        warnings.append(RiskWarning(
            level=RiskLevel.CRITICAL,
            category='guardianship',
            title='Minor Children Without Guardian',
            message='You have minor children but have not appointed a guardian.',
            suggestion=(
                'Without a guardian appointment, decisions about who cares for your children '
                'may be made by the court or child safety authorities.'
            )
        ))
    
    # Check for minor children without minor trusts
    if context.has_minor_children and not context.has_minor_trusts:
        warnings.append(RiskWarning(
            level=RiskLevel.WARNING,
            category='minor_trusts',
            title='Minor Children Without Trust Provisions',
            message='You have minor children but have not enabled trust provisions.',
            suggestion=(
                'Without trust provisions, any inheritance for minor children may need to be '
                'held by the Public Trustee until they turn 18.'
            )
        ))
    
    # Check for percentage distribution not summing to 100
    if context.has_percentages and abs(context.percentage_sum - 100.0) > 0.01:
        warnings.append(RiskWarning(
            level=RiskLevel.CRITICAL,
            category='distribution',
            title='Residue Percentages Do Not Sum to 100%',
            message=f'Your residue percentages sum to {context.percentage_sum:.1f}%, not 100%.',
            suggestion='This may cause legal uncertainty about how the residue should be distributed.'
        ))
    
    # Check for no beneficiaries
    if len(context.beneficiaries) == 0:
        warnings.append(RiskWarning(
            level=RiskLevel.CRITICAL,
            category='beneficiaries',
            title='No Beneficiaries',
            message='You have not named any beneficiaries.',
            suggestion='Without beneficiaries, your estate may pass according to intestacy laws.'
        ))
    
    # Check for partner but no provision
    if context.has_partner and context.distribution_scheme == 'equal_children':
        warnings.append(RiskWarning(
            level=RiskLevel.INFO,
            category='distribution',
            title='Partner Excluded from Distribution',
            message='You have a partner but your distribution scheme does not include them.',
            suggestion='Consider whether this reflects your intentions, as partners may have legal claims.'
        ))
    
    # Check for exclusions
    if context.has_exclusions:
        warnings.append(RiskWarning(
            level=RiskLevel.INFO,
            category='exclusions',
            title='Persons Excluded from Will',
            message='You have excluded one or more persons from your will.',
            suggestion=(
                'Excluded persons may challenge your will. Consider documenting your reasons '
                'separately with your solicitor.'
            )
        ))
    
    # Check for business interests without details
    if context.business_enabled and not context.has_business_interests:
        warnings.append(RiskWarning(
            level=RiskLevel.WARNING,
            category='business',
            title='Business Interests Enabled But Not Detailed',
            message='You indicated you have business interests but did not provide details.',
            suggestion='Consider seeking legal advice about business succession planning.'
        ))
    
    # Check for digital assets without instructions
    if context.digital_assets_enabled and not context.digital_assets_instructions_location:
        warnings.append(RiskWarning(
            level=RiskLevel.INFO,
            category='digital_assets',
            title='Digital Assets Without Instructions Location',
            message='You have enabled digital assets but not specified where instructions are kept.',
            suggestion='Consider creating a secure record of your digital asset instructions.'
        ))
    
    # Check for short survivorship period
    if context.survivorship_days < 30:
        warnings.append(RiskWarning(
            level=RiskLevel.INFO,
            category='survivorship',
            title='Short Survivorship Period',
            message=f'Your survivorship period is only {context.survivorship_days} days.',
            suggestion='A longer period (e.g., 30 days) may simplify estate administration.'
        ))
    
    # Check for pets with cash gift but no carer
    if context.pets_enabled and context.pets_cash_gift and not context.pets_carer_name:
        warnings.append(RiskWarning(
            level=RiskLevel.WARNING,
            category='pets',
            title='Pet Gift Without Carer',
            message='You have provided a cash gift for pets but not named a carer.',
            suggestion='Consider naming a specific person to care for your pets.'
        ))
    
    # Check for same person as executor and guardian
    if context.guardian and context.executors:
        guardian_name = context.guardian.full_name.lower()
        for executor in context.executors:
            if executor.full_name.lower() == guardian_name:
                warnings.append(RiskWarning(
                    level=RiskLevel.INFO,
                    category='appointments',
                    title='Same Person as Executor and Guardian',
                    message=f'{executor.full_name} is appointed as both executor and guardian.',
                    suggestion='This is common and often practical, but consider potential conflicts of interest.'
                ))
                break
    
    # Check for complex distribution
    if context.has_percentages and len(context.residue_beneficiaries) > 3:
        warnings.append(RiskWarning(
            level=RiskLevel.INFO,
            category='distribution',
            title='Complex Distribution Scheme',
            message='You have a complex distribution with multiple beneficiaries and percentages.',
            suggestion='Consider whether this complexity is necessary and how it may affect administration costs.'
        ))
    
    return warnings


def generate_clause_explainability(context: WillContext) -> Dict[str, Any]:
    """
    Generate explainability information for each clause in the will.
    
    Args:
        context: The will context
        
    Returns:
        Dictionary with clause-by-clause explainability
    """
    selected_clauses = select_clauses(context)
    
    clause_explanations = []
    for i, clause_id in enumerate(selected_clauses, 1):
        explanation = {
            'number': i,
            'clause_id': clause_id.value,
            'title': get_clause_title(clause_id),
            'purpose': _get_clause_purpose(clause_id),
            'when_applies': _get_clause_when_applies(clause_id, context),
            'key_points': _get_clause_key_points(clause_id, context),
        }
        clause_explanations.append(explanation)
    
    return {
        'total_clauses': len(clause_explanations),
        'clauses': clause_explanations
    }


def _get_clause_purpose(clause_id: ClauseId) -> str:
    """Get the purpose of a clause."""
    purposes = {
        ClauseId.TITLE_IDENTIFICATION: 
            'Identifies you as the will maker and establishes this document as your last will.',
        ClauseId.REVOCATION: 
            'Cancels all previous wills and codicils to prevent confusion.',
        ClauseId.DEFINITIONS: 
            'Sets out how key terms are interpreted throughout the will.',
        ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES: 
            'Names the people who will manage your estate and carry out your wishes.',
        ClauseId.FUNERAL_WISHES: 
            'Records your preferences for funeral arrangements.',
        ClauseId.GUARDIANSHIP: 
            'Appoints someone to care for your minor children.',
        ClauseId.DISTRIBUTION_OVERVIEW: 
            'Provides a summary of how your estate will be distributed.',
        ClauseId.SPECIFIC_GIFTS: 
            'Details particular items or amounts to be given to specific people.',
        ClauseId.RESIDUE_DISTRIBUTION: 
            'Directs how the remainder of your estate should be distributed.',
        ClauseId.SURVIVORSHIP: 
            'Sets the period a beneficiary must survive you to inherit.',
        ClauseId.SUBSTITUTION: 
            'Provides what happens if a beneficiary dies before you.',
        ClauseId.MINOR_TRUSTS: 
            'Establishes how inheritances for minors will be managed.',
        ClauseId.ADMINISTRATIVE_POWERS: 
            'Grants powers to your executors to manage the estate.',
        ClauseId.DIGITAL_ASSETS: 
            'Provides for the management of your digital assets.',
        ClauseId.PETS: 
            'Makes provision for the care of your pets.',
        ClauseId.BUSINESS_INTERESTS: 
            'Directs how your business interests should be handled.',
        ClauseId.EXCLUSION_NOTE: 
            'Notes any persons who are intentionally excluded.',
        ClauseId.LIFE_SUSTAINING_STATEMENT: 
            'Expresses your wishes about life-sustaining treatment.',
        ClauseId.ATTESTATION: 
            'Provides for proper signing and witnessing of the will.',
    }
    return purposes.get(clause_id, 'Standard will provision.')


def _get_clause_when_applies(clause_id: ClauseId, context: WillContext) -> str:
    """Get when a clause applies."""
    when_applies = {
        ClauseId.TITLE_IDENTIFICATION: 'Always applies.',
        ClauseId.REVOCATION: 'Always applies.',
        ClauseId.DEFINITIONS: 'Always applies.',
        ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES: 'Always applies.',
        ClauseId.FUNERAL_WISHES: 'Applies because you have expressed funeral wishes.',
        ClauseId.GUARDIANSHIP: 'Applies because you have minor children and have appointed a guardian.',
        ClauseId.DISTRIBUTION_OVERVIEW: 'Applies because you have a complex distribution scheme.',
        ClauseId.SPECIFIC_GIFTS: 'Applies because you have made specific gifts.',
        ClauseId.RESIDUE_DISTRIBUTION: 'Always applies.',
        ClauseId.SURVIVORSHIP: 'Always applies.',
        ClauseId.SUBSTITUTION: 'Applies because you have configured substitution rules.',
        ClauseId.MINOR_TRUSTS: 'Applies because you have minor beneficiaries or children.',
        ClauseId.ADMINISTRATIVE_POWERS: 'Always applies.',
        ClauseId.DIGITAL_ASSETS: 'Applies because you have enabled digital assets provisions.',
        ClauseId.PETS: 'Applies because you have made provision for pets.',
        ClauseId.BUSINESS_INTERESTS: 'Applies because you have business interests.',
        ClauseId.EXCLUSION_NOTE: 'Applies because you have noted exclusions.',
        ClauseId.LIFE_SUSTAINING_STATEMENT: 'Applies because you have expressed wishes about life-sustaining treatment.',
        ClauseId.ATTESTATION: 'Always applies - required for valid execution.',
    }
    
    default = 'Applies based on your selections.'
    return when_applies.get(clause_id, default)


def _get_clause_key_points(clause_id: ClauseId, context: WillContext) -> List[str]:
    """Get key points for a clause."""
    key_points = {
        ClauseId.TITLE_IDENTIFICATION: [
            'Identifies you by full name and address',
            'Declares this is your last will',
            'Revokes all previous wills'
        ],
        ClauseId.REVOCATION: [
            'Cancels all prior wills and codicils',
            'Ensures only this will governs your estate'
        ],
        ClauseId.DEFINITIONS: [
            'Defines key terms used in the will',
            'Ensures consistent interpretation'
        ],
        ClauseId.APPOINTMENT_EXECUTORS_TRUSTEES: [
            f"Appoints {len(context.executors)} executor(s)",
            'Grants authority to administer the estate',
            'May include backup executors'
        ],
        ClauseId.FUNERAL_WISHES: [
            'Records your funeral preferences',
            'Not legally binding but provides guidance',
            'Executors have final discretion'
        ],
        ClauseId.GUARDIANSHIP: [
            f"Appoints {context.guardian.full_name if context.guardian else 'a guardian'} for minor children",
            'Takes effect only if both parents are deceased',
            'Subject to court approval if contested'
        ],
        ClauseId.SPECIFIC_GIFTS: [
            f"Includes {len(context.specific_gifts)} specific gift(s)",
            'Distributed before residue',
            'May fail if asset not owned at death'
        ],
        ClauseId.RESIDUE_DISTRIBUTION: [
            f"Distributes residue to {len(context.residue_beneficiaries)} beneficiary/beneficiaries",
            'Covers everything not specifically gifted',
            'Subject to payment of debts and expenses'
        ],
        ClauseId.SURVIVORSHIP: [
            f"Sets survivorship period at {context.survivorship_days} days",
            'Prevesting lapsed gifts',
            'Simplifies administration'
        ],
        ClauseId.MINOR_TRUSTS: [
            f"Holds gifts for minors until age {context.minor_trusts_vesting_age}",
            'Trustees manage the assets',
            'Income may be used for beneficiary\'s benefit'
        ],
        ClauseId.ADMINISTRATIVE_POWERS: [
            'Grants powers to sell assets',
            'Allows investment of estate funds',
            'Authorizes legal proceedings'
        ],
        ClauseId.ATTESTATION: [
            'Requires signature by you',
            'Requires two independent witnesses',
            'Must be signed in presence of each other'
        ],
    }
    
    return key_points.get(clause_id, ['Standard provision'])


def generate_execution_checklist_summary(context: WillContext) -> Dict[str, Any]:
    """
    Generate a summary of execution requirements for the will.
    
    Args:
        context: The will context
        
    Returns:
        Dictionary with execution requirements
    """
    return {
        'signing_requirements': {
            'must_be_signed_by': context.will_maker.full_name,
            'number_of_witnesses': 2,
            'witness_requirements': [
                'Must be adults (18+ years)',
                'Must not be beneficiaries',
                'Must not be spouses of beneficiaries',
                'Must witness signature in your presence',
                'Must sign in presence of each other'
            ],
        },
        'who_cannot_witness': [
            'Any beneficiary named in the will',
            'The spouse or partner of any beneficiary',
            'Anyone who is blind (cannot see you sign)',
            'Anyone who does not understand the nature of the document'
        ],
        'storage_recommendations': [
            'Store in a safe, dry place',
            'Inform your executors where the will is kept',
            'Consider storing with your solicitor',
            'Do not attach anything to the will (staples, paperclips)'
        ],
        'next_steps': [
            'Print the will on A4 paper (single-sided)',
            'Review the will carefully before signing',
            'Arrange for two independent witnesses',
            'Sign in the presence of both witnesses',
            'Have witnesses sign in your presence and each other\'s presence',
            'Date the will on the day of signing',
            'Store the original safely'
        ]
    }
