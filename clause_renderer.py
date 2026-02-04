"""
Clause Renderer Module

Renders clause blocks into a unified document plan.
Uses Jinja2 macros from modular_will_template.j2 to produce content blocks.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from jinja2 import Environment, PackageLoader, select_autoescape

from app.context_builder import WillContext
from app.clause_logic import (
    select_clauses, get_clause_title, get_clause_number,
    CLAUSE_TITLE_IDENTIFICATION, CLAUSE_REVOCATION, CLAUSE_DEFINITIONS,
    CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES, CLAUSE_FUNERAL_WISHES,
    CLAUSE_GUARDIANSHIP, CLAUSE_DISTRIBUTION_OVERVIEW, CLAUSE_SPECIFIC_GIFTS,
    CLAUSE_RESIDUE_DISTRIBUTION, CLAUSE_SURVIVORSHIP, CLAUSE_SUBSTITUTION,
    CLAUSE_MINOR_TRUSTS, CLAUSE_ADMINISTRATIVE_POWERS, CLAUSE_DIGITAL_ASSETS,
    CLAUSE_PETS, CLAUSE_BUSINESS_INTERESTS, CLAUSE_EXCLUSION_NOTE,
    CLAUSE_LIFE_SUSTAINING_STATEMENT, CLAUSE_ATTESTATION
)


@dataclass
class ContentBlock:
    """A block of content within a clause."""
    type: str  # 'paragraph', 'bullet_list', 'numbered_list', 'table', 'signature_block', 'page_break'
    content: Any
    style: str = 'normal'
    indent_level: int = 0


@dataclass
class DocumentPlanItem:
    """A clause in the document plan."""
    id: str
    title: str
    numbering_level: int  # 1 for main clauses, 2 for sub-clauses
    content_blocks: List[ContentBlock] = field(default_factory=list)
    clause_number: int = 0


# Initialize Jinja environment
jinja_env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)


def render_document_plan(context: WillContext) -> List[DocumentPlanItem]:
    """
    Render the complete document plan from context.
    
    Args:
        context: The will context with all entities and flags
    
    Returns:
        List of document plan items (clauses with content blocks)
    """
    # Select which clauses to include
    clause_ids = select_clauses(context)
    
    # Render each clause
    document_plan = []
    for i, clause_id in enumerate(clause_ids):
        clause_number = i + 1
        item = _render_clause(clause_id, context, clause_number)
        if item:
            document_plan.append(item)
    
    return document_plan


def _render_clause(clause_id: str, context: WillContext, clause_number: int) -> Optional[DocumentPlanItem]:
    """
    Render a single clause into a document plan item.
    
    Args:
        clause_id: The clause identifier
        context: The will context
        clause_number: The clause number in sequence
    
    Returns:
        DocumentPlanItem or None
    """
    title = get_clause_title(clause_id)
    
    # Route to specific renderer based on clause type
    renderers = {
        CLAUSE_TITLE_IDENTIFICATION: _render_title_identification,
        CLAUSE_REVOCATION: _render_revocation,
        CLAUSE_DEFINITIONS: _render_definitions,
        CLAUSE_APPOINTMENT_EXECUTORS_TRUSTEES: _render_appointment_executors,
        CLAUSE_FUNERAL_WISHES: _render_funeral_wishes,
        CLAUSE_GUARDIANSHIP: _render_guardianship,
        CLAUSE_DISTRIBUTION_OVERVIEW: _render_distribution_overview,
        CLAUSE_SPECIFIC_GIFTS: _render_specific_gifts,
        CLAUSE_RESIDUE_DISTRIBUTION: _render_residue_distribution,
        CLAUSE_SURVIVORSHIP: _render_survivorship,
        CLAUSE_SUBSTITUTION: _render_substitution,
        CLAUSE_MINOR_TRUSTS: _render_minor_trusts,
        CLAUSE_ADMINISTRATIVE_POWERS: _render_administrative_powers,
        CLAUSE_DIGITAL_ASSETS: _render_digital_assets,
        CLAUSE_PETS: _render_pets,
        CLAUSE_BUSINESS_INTERESTS: _render_business_interests,
        CLAUSE_EXCLUSION_NOTE: _render_exclusion_note,
        CLAUSE_LIFE_SUSTAINING_STATEMENT: _render_life_sustaining,
        CLAUSE_ATTESTATION: _render_attestation,
    }
    
    renderer = renderers.get(clause_id)
    if not renderer:
        return None
    
    content_blocks = renderer(context)
    
    return DocumentPlanItem(
        id=clause_id,
        title=title,
        numbering_level=1,
        content_blocks=content_blocks,
        clause_number=clause_number
    )


def _render_title_identification(context: WillContext) -> List[ContentBlock]:
    """Render title and identification clause."""
    blocks = []
    
    # Main title
    blocks.append(ContentBlock(
        type='heading1',
        content='LAST WILL AND TESTAMENT',
        style='title'
    ))
    
    # Will maker identification paragraph
    will_maker_text = (
        f'I, {context.will_maker.full_name}, of {context.will_maker.address.to_single_line()}, '
        f'{context.will_maker.occupation}, revoke all former wills and codicils made by me '
        f'and declare this to be my Last Will and Testament.'
    )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=will_maker_text,
        style='normal'
    ))
    
    return blocks


def _render_revocation(context: WillContext) -> List[ContentBlock]:
    """Render revocation clause."""
    blocks = []
    
    blocks.append(ContentBlock(
        type='paragraph',
        content='I revoke all wills and codicils previously made by me.',
        style='normal'
    ))
    
    return blocks


def _render_definitions(context: WillContext) -> List[ContentBlock]:
    """Render definitions clause."""
    blocks = []
    
    blocks.append(ContentBlock(
        type='paragraph',
        content='In this Will, unless the context otherwise requires:',
        style='normal'
    ))
    
    definitions = [
        ('"Beneficiary"', 'means a person or entity entitled to receive a gift under this Will.'),
        ('"Child"', 'includes a biological child, adopted child, and stepchild.'),
        ('"Estate"', 'means all property and assets which I own at my death.'),
        ('"Executor"', 'means the person or persons appointed to administer my Estate.'),
        ('"Minor"', 'means a person under the age of 18 years.'),
        ('"Residue"', 'means what remains of my Estate after payment of debts, funeral and testamentary expenses, and all specific gifts.'),
        ('"Survivorship Period"', f'means the period of {context.survivorship_days} days from my death.'),
    ]
    
    for term, definition in definitions:
        blocks.append(ContentBlock(
            type='bullet_item',
            content={'term': term, 'definition': definition},
            style='definition',
            indent_level=1
        ))
    
    return blocks


def _render_appointment_executors(context: WillContext) -> List[ContentBlock]:
    """Render appointment of executors and trustees clause."""
    blocks = []
    
    # Primary executors
    if context.executors:
        if len(context.executors) == 1:
            executor = context.executors[0]
            text = (
                f'I appoint {executor.full_name}, of {executor.address.to_single_line()}, '
                f'to be the Executor and Trustee of my Estate.'
            )
        else:
            executor_names = [e.full_name for e in context.executors]
            if len(executor_names) == 2:
                names_text = f'{executor_names[0]} and {executor_names[1]}'
            else:
                names_text = ', '.join(executor_names[:-1]) + f', and {executor_names[-1]}'
            
            text = f'I appoint {names_text} to be the Executors and Trustees of my Estate.'
        
        blocks.append(ContentBlock(
            type='paragraph',
            content=text,
            style='normal'
        ))
    
    # Backup executors
    if context.backup_executors:
        if len(context.backup_executors) == 1:
            backup = context.backup_executors[0]
            text = (
                f'If {backup.full_name} is unable or unwilling to act, '
                f'I appoint {backup.full_name}, of {backup.address.to_single_line()}, '
                f'to be the substitute Executor and Trustee.'
            )
        else:
            backup_names = [e.full_name for e in context.backup_executors]
            if len(backup_names) == 2:
                names_text = f'{backup_names[0]} and {backup_names[1]}'
            else:
                names_text = ', '.join(backup_names[:-1]) + f', and {backup_names[-1]}'
            
            text = (
                f'If any of my appointed Executors is unable or unwilling to act, '
                f'I appoint {names_text} to be the substitute Executors and Trustees.'
            )
        
        blocks.append(ContentBlock(
            type='paragraph',
            content=text,
            style='normal'
        ))
    
    return blocks


def _render_funeral_wishes(context: WillContext) -> List[ContentBlock]:
    """Render funeral wishes clause."""
    blocks = []
    
    preference_text = {
        'burial': 'burial',
        'cremation': 'cremation',
        'no_preference': 'no preference as to burial or cremation'
    }
    
    preference = preference_text.get(context.funeral_preference, 'no preference')
    
    text = f'I express the wish that my body be disposed of by {preference}.'
    
    if context.funeral_notes:
        text += f' {context.funeral_notes}'
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    return blocks


def _render_guardianship(context: WillContext) -> List[ContentBlock]:
    """Render guardianship clause."""
    blocks = []
    
    if context.guardian:
        text = (
            f'If at my death any of my children are minors, '
            f'I appoint {context.guardian.full_name}, of {context.guardian.address.to_single_line()}, '
            f'to be the guardian of such minor children.'
        )
        
        blocks.append(ContentBlock(
            type='paragraph',
            content=text,
            style='normal'
        ))
        
        if context.backup_guardian:
            backup_text = (
                f'If {context.guardian.full_name} is unable or unwilling to act as guardian, '
                f'I appoint {context.backup_guardian.full_name}, of '
                f'{context.backup_guardian.address.to_single_line()}, to be the substitute guardian.'
            )
            
            blocks.append(ContentBlock(
                type='paragraph',
                content=backup_text,
                style='normal'
            ))
    
    return blocks


def _render_distribution_overview(context: WillContext) -> List[ContentBlock]:
    """Render distribution overview clause."""
    blocks = []
    
    scheme_descriptions = {
        'partner_then_children_equal': 
            'My Estate shall be distributed first to my partner, and if my partner does not survive me, '
            'equally among my children.',
        'children_equal': 
            'My Estate shall be distributed equally among my children.',
        'percentages_named': 
            'My Estate shall be distributed among the named beneficiaries in the percentages specified.',
        'specific_gifts_then_residue': 
            'I make specific gifts as detailed below, and the residue of my Estate shall be distributed '
            'as specified.',
        'custom_structured': 
            'My Estate shall be distributed according to the following structured plan.',
    }
    
    description = scheme_descriptions.get(
        context.distribution_scheme, 
        'My Estate shall be distributed as specified in this Will.'
    )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=description,
        style='normal'
    ))
    
    return blocks


def _render_specific_gifts(context: WillContext) -> List[ContentBlock]:
    """Render specific gifts clause."""
    blocks = []
    
    if context.specific_gifts:
        blocks.append(ContentBlock(
            type='paragraph',
            content='I give the following specific gifts:',
            style='normal'
        ))
        
        for i, gift in enumerate(context.specific_gifts, 1):
            if gift.gift_type == 'cash':
                gift_text = (
                    f'{i}. To {gift.beneficiary_name}, the sum of '
                    f'${gift.cash_amount:,.2f}.'
                )
            else:  # item
                gift_text = (
                    f'{i}. To {gift.beneficiary_name}, my {gift.item_description}.'
                )
            
            blocks.append(ContentBlock(
                type='numbered_item',
                content=gift_text,
                style='gift_item',
                indent_level=1
            ))
    
    return blocks


def _render_residue_distribution(context: WillContext) -> List[ContentBlock]:
    """Render residue distribution clause."""
    blocks = []
    
    if context.residue_beneficiaries:
        if len(context.residue_beneficiaries) == 1:
            beneficiary = context.residue_beneficiaries[0]
            text = (
                f'I give the residue of my Estate to {beneficiary.beneficiary_name}.'
            )
            if beneficiary.share_percent and beneficiary.share_percent != 100:
                text = (
                    f'I give {beneficiary.share_percent}% of the residue of my Estate '
                    f'to {beneficiary.beneficiary_name}.'
                )
        else:
            text = 'I give the residue of my Estate as follows:'
            blocks.append(ContentBlock(
                type='paragraph',
                content=text,
                style='normal'
            ))
            
            for i, beneficiary in enumerate(context.residue_beneficiaries, 1):
                share = beneficiary.share_percent or (100 / len(context.residue_beneficiaries))
                item_text = (
                    f'{i}. {share}% to {beneficiary.beneficiary_name}'
                )
                blocks.append(ContentBlock(
                    type='numbered_item',
                    content=item_text,
                    style='residue_item',
                    indent_level=1
                ))
            
            return blocks
    else:
        # Default residue clause
        text = 'I give the residue of my Estate to my executors upon the trusts hereinafter declared.'
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    return blocks


def _render_survivorship(context: WillContext) -> List[ContentBlock]:
    """Render survivorship clause."""
    blocks = []
    
    days_text = {
        0: 'immediately upon my death',
        7: '7 days',
        14: '14 days',
        30: '30 days',
        60: '60 days'
    }
    
    period = days_text.get(context.survivorship_days, f'{context.survivorship_days} days')
    
    if context.survivorship_days == 0:
        text = (
            'A beneficiary under this Will must survive me to take a gift. '
            'No survivorship period applies.'
        )
    else:
        text = (
            f'A beneficiary under this Will must survive me by {period} '
            f'to take a gift under this Will. '
            f'If a beneficiary does not survive me by this period, '
            f'they shall be treated as having predeceased me.'
        )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    return blocks


def _render_substitution(context: WillContext) -> List[ContentBlock]:
    """Render substitution clause."""
    blocks = []
    
    rule_texts = {
        'to_their_children': 
            'If a beneficiary predeceases me, their share shall pass to their children '
            'who survive me, in equal shares.',
        'redistribute_among_remaining': 
            'If a beneficiary predeceases me, their share shall be redistributed '
            'among the remaining beneficiaries in proportion to their respective shares.',
        'to_alternate_beneficiary': 
            f'If a beneficiary predeceases me, their share shall pass to '
            f'{context.alternate_beneficiary_name}.',
    }
    
    text = rule_texts.get(
        context.substitution_rule,
        'If a beneficiary predeceases me, their share shall lapse.'
    )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    return blocks


def _render_minor_trusts(context: WillContext) -> List[ContentBlock]:
    """Render minor trusts clause."""
    blocks = []
    
    text = (
        f'If any beneficiary under this Will is a minor at the time of distribution, '
        f'their share shall be held in trust until they attain the age of '
        f'{context.minor_trusts_vesting_age} years.'
    )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    # Trustee appointment
    if context.minor_trusts_trustee_mode == 'named_trustee' and context.minor_trusts_trustee:
        trustee_text = (
            f'I appoint {context.minor_trusts_trustee.full_name}, of '
            f'{context.minor_trusts_trustee.address.to_single_line()}, '
            f'to be the trustee of such trust.'
        )
    else:
        trustee_text = (
            'My Executors shall be the trustees of any trust created under this Will.'
        )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=trustee_text,
        style='normal'
    ))
    
    # Trust powers
    blocks.append(ContentBlock(
        type='paragraph',
        content=(
            'The trustees may apply the income and capital of the trust '
            'for the maintenance, education, advancement, or benefit of '
            'the beneficiary in their absolute discretion.'
        ),
        style='normal'
    ))
    
    return blocks


def _render_administrative_powers(context: WillContext) -> List[ContentBlock]:
    """Render administrative powers clause."""
    blocks = []
    
    blocks.append(ContentBlock(
        type='paragraph',
        content='My Executors and Trustees shall have the following powers:',
        style='normal'
    ))
    
    powers = [
        'To sell, convert, call in, and dispose of any part of my Estate as they think fit.',
        'To pay or compromise any debt or claim against my Estate.',
        'To employ professional advisers and agents as they consider necessary.',
        'To invest trust funds in any investments authorized by law for trust investments.',
        'To apply income for the maintenance of beneficiaries during the administration of my Estate.',
        'To delegate powers and duties as permitted by law.',
    ]
    
    for power in powers:
        blocks.append(ContentBlock(
            type='bullet_item',
            content=power,
            style='power_item',
            indent_level=1
        ))
    
    return blocks


def _render_digital_assets(context: WillContext) -> List[ContentBlock]:
    """Render digital assets clause."""
    blocks = []
    
    if context.digital_assets_authority:
        text = (
            'I authorize my Executors to access, manage, and dispose of my digital assets. '
            'This includes access to the following categories: '
        )
        
        categories = []
        category_names = {
            'email': 'email accounts',
            'social_media': 'social media accounts',
            'cloud_storage': 'cloud storage accounts',
            'crypto': 'cryptocurrency holdings'
        }
        
        for cat in context.digital_assets_categories:
            categories.append(category_names.get(cat, cat))
        
        if categories:
            text += ', '.join(categories) + '.'
        
        if context.digital_assets_instructions_location:
            text += (
                f' Detailed instructions for accessing these assets are located at: '
                f'{context.digital_assets_instructions_location}.'
            )
        
        blocks.append(ContentBlock(
            type='paragraph',
            content=text,
            style='normal'
        ))
    
    return blocks


def _render_pets(context: WillContext) -> List[ContentBlock]:
    """Render pets clause."""
    blocks = []
    
    text = (
        f'I have {context.pets_count} pet(s): {context.pets_summary}. '
        f'I give my pets to {context.pets_carer_name}, of '
        f'{context.pets_carer_address.to_single_line()}, '
        f'for care and custody.'
    )
    
    if context.pets_cash_gift:
        text += (
            f' I also give to {context.pets_carer_name} the sum of '
            f'${context.pets_cash_gift:,.2f} for the care and maintenance of my pets.'
        )
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    return blocks


def _render_business_interests(context: WillContext) -> List[ContentBlock]:
    """Render business interests clause."""
    blocks = []
    
    if context.business_interests:
        blocks.append(ContentBlock(
            type='paragraph',
            content='I direct that my business interests be dealt with as follows:',
            style='normal'
        ))
        
        for i, interest in enumerate(context.business_interests, 1):
            interest_type_names = {
                'sole_trader': 'sole trader business',
                'company_shareholding': 'company shareholding',
                'partnership': 'partnership interest',
                'trust_interest': 'trust interest'
            }
            
            type_name = interest_type_names.get(interest.interest_type, 'business interest')
            
            item_text = (
                f'{i}. My {type_name} in {interest.entity_name} '
                f'shall pass to {interest.recipient_name}.'
            )
            
            blocks.append(ContentBlock(
                type='numbered_item',
                content=item_text,
                style='business_item',
                indent_level=1
            ))
    
    return blocks


def _render_exclusion_note(context: WillContext) -> List[ContentBlock]:
    """Render exclusion note clause."""
    blocks = []
    
    if context.exclusions:
        for exclusion in context.exclusions:
            category_names = {
                'former_partner': 'former partner',
                'child': 'child',
                'stepchild': 'stepchild',
                'dependant_other': 'dependant'
            }
            
            category = category_names.get(exclusion.category, exclusion.category)
            
            text = (
                f'I have made no provision in this Will for my {category}, '
                f'{exclusion.person_name}.'
            )
            
            if exclusion.reasons:
                reason_texts = {
                    'already_provided_for': 'they have already been provided for during my lifetime',
                    'estrangement': 'of estrangement',
                    'financial_independence': 'they are financially independent',
                    'other_structured': exclusion.other_note if exclusion.other_note else 'other reasons'
                }
                
                reasons_list = [reason_texts.get(r, r) for r in exclusion.reasons]
                text += ' This is because ' + ', '.join(reasons_list) + '.'
            
            blocks.append(ContentBlock(
                type='paragraph',
                content=text,
                style='normal'
            ))
    
    return blocks


def _render_life_sustaining(context: WillContext) -> List[ContentBlock]:
    """Render life sustaining treatment statement."""
    blocks = []
    
    template_texts = {
        'comfort_and_dignity_prioritised': (
            'If I have a terminal illness or injury, or am in a persistent vegetative state, '
            'I direct that my comfort and dignity be prioritised. '
            'I do not wish to receive life-sustaining treatment if the burdens outweigh the benefits.'
        ),
        'palliative_only_in_terminal_or_permanent_unconsciousness': (
            'If I have a terminal condition or am permanently unconscious, '
            'I direct that only palliative care be provided to maintain my comfort. '
            'I do not wish to receive treatment that would merely prolong the dying process.'
        ),
        'prolong_life_if_reasonable': (
            'I wish for all reasonable measures to be taken to prolong my life, '
            'provided that such measures do not cause undue suffering.'
        )
    }
    
    text = template_texts.get(
        context.life_sustaining_template,
        'I have expressed my wishes regarding life sustaining treatment.'
    )
    
    if context.life_sustaining_values:
        value_texts = {
            'comfort': 'comfort',
            'dignity': 'dignity',
            'palliative_care': 'palliative care',
            'avoid_burdensome_treatment': 'avoidance of burdensome treatment'
        }
        
        values = [value_texts.get(v, v) for v in context.life_sustaining_values]
        text += f' My values include: {", ".join(values)}.'
    
    blocks.append(ContentBlock(
        type='paragraph',
        content=text,
        style='normal'
    ))
    
    return blocks


def _render_attestation(context: WillContext) -> List[ContentBlock]:
    """Render attestation and execution clause."""
    blocks = []
    
    # Execution statement
    blocks.append(ContentBlock(
        type='paragraph',
        content='SIGNED by the Testator as their Last Will and Testament:',
        style='normal'
    ))
    
    # Signature block for will maker
    blocks.append(ContentBlock(
        type='signature_block',
        content={
            'label': 'Signature of Will Maker',
            'name': context.will_maker.full_name,
            'date_label': 'Date',
            'lines': 3
        },
        style='signature'
    ))
    
    # Witness statement
    blocks.append(ContentBlock(
        type='paragraph',
        content=(
            'SIGNED by the above-named Testator in our presence '
            'and attested by us in the presence of the Testator and each other.'
        ),
        style='normal'
    ))
    
    # Witness 1 signature block
    blocks.append(ContentBlock(
        type='signature_block',
        content={
            'label': 'Witness 1',
            'name_label': 'Name (print)',
            'address_label': 'Address',
            'occupation_label': 'Occupation',
            'date_label': 'Date',
            'lines': 4
        },
        style='signature'
    ))
    
    # Witness 2 signature block
    blocks.append(ContentBlock(
        type='signature_block',
        content={
            'label': 'Witness 2',
            'name_label': 'Name (print)',
            'address_label': 'Address',
            'occupation_label': 'Occupation',
            'date_label': 'Date',
            'lines': 4
        },
        style='signature'
    ))
    
    return blocks


def document_plan_to_dict(document_plan: List[DocumentPlanItem]) -> List[Dict[str, Any]]:
    """
    Convert document plan to dictionary for serialization.
    
    Args:
        document_plan: List of DocumentPlanItem
    
    Returns:
        List of dictionaries
    """
    result = []
    for item in document_plan:
        result.append({
            'id': item.id,
            'title': item.title,
            'clause_number': item.clause_number,
            'numbering_level': item.numbering_level,
            'content_blocks': [
                {
                    'type': block.type,
                    'content': block.content,
                    'style': block.style,
                    'indent_level': block.indent_level
                }
                for block in item.content_blocks
            ]
        })
    return result
