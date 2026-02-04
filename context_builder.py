"""
Context Builder Module

Transforms raw validated payload into a normalized context object with derived flags.
All derived flags are computed in one place only.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.utils import is_minor_at_date


@dataclass
class Address:
    """Structured address."""
    street: str = ''
    suburb: str = ''
    state: str = ''
    postcode: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Address':
        if not data:
            return cls()
        return cls(
            street=data.get('street', ''),
            suburb=data.get('suburb', ''),
            state=data.get('state', ''),
            postcode=data.get('postcode', '')
        )
    
    def to_single_line(self) -> str:
        parts = [p for p in [self.street, self.suburb, self.state, self.postcode] if p]
        return ', '.join(parts)
    
    def to_multiline(self) -> List[str]:
        lines = [self.street] if self.street else []
        line2 = ' '.join([p for p in [self.suburb, self.state, self.postcode] if p])
        if line2:
            lines.append(line2)
        return lines


@dataclass
class Person:
    """Base person entity."""
    full_name: str = ''
    address: Address = field(default_factory=Address)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            address=Address.from_dict(data.get('address', {}))
        )


@dataclass
class WillMaker:
    """Will maker entity."""
    full_name: str = ''
    dob: Optional[str] = None
    occupation: str = ''
    address: Address = field(default_factory=Address)
    email: str = ''
    phone: str = ''
    relationship_status: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WillMaker':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            dob=data.get('dob'),
            occupation=data.get('occupation', ''),
            address=Address.from_dict(data.get('address', {})),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            relationship_status=data.get('relationship_status', '')
        )


@dataclass
class Partner:
    """Partner entity."""
    full_name: str = ''
    dob: Optional[str] = None
    address: Address = field(default_factory=Address)
    email: str = ''
    phone: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Partner':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            dob=data.get('dob'),
            address=Address.from_dict(data.get('address', {})),
            email=data.get('email', ''),
            phone=data.get('phone', '')
        )


@dataclass
class Child:
    """Child entity."""
    full_name: str = ''
    dob: Optional[str] = None
    relationship_type: str = ''
    is_expected_to_be_minor_at_death: bool = False
    special_needs: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Child':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            dob=data.get('dob'),
            relationship_type=data.get('relationship_type', ''),
            is_expected_to_be_minor_at_death=data.get('is_expected_to_be_minor_at_death', False),
            special_needs=data.get('special_needs', False)
        )


@dataclass
class Dependant:
    """Other dependant entity."""
    full_name: str = ''
    relationship_category: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dependant':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            relationship_category=data.get('relationship_category', '')
        )


@dataclass
class Executor:
    """Executor entity."""
    full_name: str = ''
    relationship: str = ''
    address: Address = field(default_factory=Address)
    phone: str = ''
    email: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Executor':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            relationship=data.get('relationship', ''),
            address=Address.from_dict(data.get('address', {})),
            phone=data.get('phone', ''),
            email=data.get('email', '')
        )


@dataclass
class Guardian:
    """Guardian entity."""
    full_name: str = ''
    relationship: str = ''
    address: Address = field(default_factory=Address)
    phone: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Guardian':
        if not data:
            return cls()
        return cls(
            full_name=data.get('full_name', ''),
            relationship=data.get('relationship', ''),
            address=Address.from_dict(data.get('address', {})),
            phone=data.get('phone', '')
        )


@dataclass
class Beneficiary:
    """Beneficiary entity."""
    id: str = ''
    type: str = 'individual'
    full_name: str = ''
    relationship: str = ''
    address: Address = field(default_factory=Address)
    abn: str = ''
    gift_role: str = ''
    residue_share_percent: Optional[float] = None
    percentage: Optional[float] = None
    cash_amount: Optional[float] = None
    item_description: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], index: int) -> 'Beneficiary':
        if not data:
            return cls()
        return cls(
            id=data.get('id', f'beneficiary_{index}'),
            type=data.get('type', 'individual'),
            full_name=data.get('full_name', ''),
            relationship=data.get('relationship', ''),
            address=Address.from_dict(data.get('address', {})),
            abn=data.get('abn', ''),
            gift_role=data.get('gift_role', ''),
            residue_share_percent=data.get('residue_share_percent'),
            percentage=data.get('percentage'),
            cash_amount=data.get('cash_amount'),
            item_description=data.get('item_description', '')
        )


@dataclass
class SpecificGift:
    """Specific gift entity."""
    beneficiary_id: str = ''
    beneficiary_name: str = ''
    gift_type: str = ''  # 'cash' or 'item'
    cash_amount: Optional[float] = None
    item_description: str = ''


@dataclass
class ResidueBeneficiary:
    """Residue beneficiary entity."""
    beneficiary_id: str = ''
    beneficiary_name: str = ''
    share_percent: Optional[float] = None


@dataclass
class BusinessInterest:
    """Business interest entity."""
    interest_type: str = ''
    entity_name: str = ''
    acn: str = ''
    abn: str = ''
    recipient_mode: str = ''
    recipient_id: Optional[str] = None
    recipient_name: str = ''
    recipient_address: Address = field(default_factory=Address)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], beneficiaries: List[Beneficiary]) -> 'BusinessInterest':
        if not data:
            return cls()
        
        recipient_mode = data.get('recipient_mode', '')
        recipient_id = data.get('recipient_id')
        recipient_name = ''
        recipient_address = Address()
        
        if recipient_mode == 'select_beneficiary' and recipient_id:
            for b in beneficiaries:
                if b.id == recipient_id:
                    recipient_name = b.full_name
                    recipient_address = b.address
                    break
        elif recipient_mode == 'new_person':
            recipient = data.get('recipient', {})
            recipient_name = recipient.get('full_name', '')
            recipient_address = Address.from_dict(recipient.get('address', {}))
        
        return cls(
            interest_type=data.get('interest_type', ''),
            entity_name=data.get('entity_name', ''),
            acn=data.get('acn', ''),
            abn=data.get('abn', ''),
            recipient_mode=recipient_mode,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            recipient_address=recipient_address
        )


@dataclass
class Exclusion:
    """Exclusion entity."""
    person_name: str = ''
    category: str = ''
    reasons: List[str] = field(default_factory=list)
    other_note: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Exclusion':
        if not data:
            return cls()
        return cls(
            person_name=data.get('person_name', ''),
            category=data.get('category', ''),
            reasons=data.get('reasons', []),
            other_note=data.get('other_note', '')
        )


@dataclass
class WillContext:
    """
    Complete context object for will generation.
    Contains all normalized entities and derived flags.
    """
    # Core entities
    will_maker: WillMaker = field(default_factory=WillMaker)
    partner: Optional[Partner] = None
    separation: Dict[str, Any] = field(default_factory=dict)
    children: List[Child] = field(default_factory=list)
    other_dependants: List[Dependant] = field(default_factory=list)
    executors: List[Executor] = field(default_factory=list)
    backup_executors: List[Executor] = field(default_factory=list)
    guardian: Optional[Guardian] = None
    backup_guardian: Optional[Guardian] = None
    beneficiaries: List[Beneficiary] = field(default_factory=list)
    specific_gifts: List[SpecificGift] = field(default_factory=list)
    residue_beneficiaries: List[ResidueBeneficiary] = field(default_factory=list)
    business_interests: List[BusinessInterest] = field(default_factory=list)
    exclusions: List[Exclusion] = field(default_factory=list)
    
    # Distribution settings
    distribution_scheme: str = ''
    survivorship_days: int = 30
    substitution_rule: str = ''
    alternate_beneficiary_id: Optional[str] = None
    alternate_beneficiary_name: str = ''
    
    # Minor trusts
    minor_trusts_enabled: bool = False
    minor_trusts_vesting_age: int = 18
    minor_trusts_trustee_mode: str = ''
    minor_trusts_trustee: Optional[Executor] = None
    
    # Optional toggles
    funeral_enabled: bool = False
    funeral_preference: str = ''
    funeral_notes: str = ''
    
    digital_assets_enabled: bool = False
    digital_assets_authority: bool = False
    digital_assets_categories: List[str] = field(default_factory=list)
    digital_assets_instructions_location: str = ''
    
    pets_enabled: bool = False
    pets_count: int = 0
    pets_summary: str = ''
    pets_carer_mode: str = ''
    pets_carer_name: str = ''
    pets_carer_address: Address = field(default_factory=Address)
    pets_cash_gift: Optional[float] = None
    
    business_enabled: bool = False
    
    exclusion_enabled: bool = False
    
    life_sustaining_enabled: bool = False
    life_sustaining_template: str = ''
    life_sustaining_values: List[str] = field(default_factory=list)
    
    # Assets overview
    assets: Dict[str, Any] = field(default_factory=dict)
    
    # Declarations
    intended_signing_date: Optional[str] = None
    
    # Derived flags (computed in build_context)
    has_partner: bool = False
    has_children: bool = False
    has_minor_children: bool = False
    has_guardianship: bool = False
    has_specific_gifts: bool = False
    has_residue_scheme: bool = False
    has_percentages: bool = False
    has_exclusions: bool = False
    has_digital_assets: bool = False
    has_pets: bool = False
    has_business_interests: bool = False
    has_funeral_wishes: bool = False
    has_life_sustaining_statement: bool = False
    has_minor_trusts: bool = False
    has_substitution: bool = False
    has_alternate_beneficiary: bool = False
    
    # Derived counts
    beneficiary_count: int = 0
    minor_beneficiary_count: int = 0
    percentage_sum: float = 0.0
    executor_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for debugging."""
        return {
            'will_maker': {
                'full_name': self.will_maker.full_name,
                'relationship_status': self.will_maker.relationship_status,
            },
            'derived_flags': {
                'has_partner': self.has_partner,
                'has_children': self.has_children,
                'has_minor_children': self.has_minor_children,
                'has_guardianship': self.has_guardianship,
                'has_specific_gifts': self.has_specific_gifts,
                'has_residue_scheme': self.has_residue_scheme,
                'has_percentages': self.has_percentages,
                'has_exclusions': self.has_exclusions,
                'has_digital_assets': self.has_digital_assets,
                'has_pets': self.has_pets,
                'has_business_interests': self.has_business_interests,
                'has_funeral_wishes': self.has_funeral_wishes,
                'has_life_sustaining_statement': self.has_life_sustaining_statement,
                'has_minor_trusts': self.has_minor_trusts,
                'has_substitution': self.has_substitution,
            },
            'counts': {
                'beneficiary_count': self.beneficiary_count,
                'minor_beneficiary_count': self.minor_beneficiary_count,
                'percentage_sum': self.percentage_sum,
                'executor_count': self.executor_count,
            }
        }


def build_context(payload: Dict[str, Any]) -> WillContext:
    """
    Build the complete will context from a validated payload.
    
    This is the single source of truth for all derived flags.
    All flag computation happens here and nowhere else.
    
    Args:
        payload: Validated form payload
    
    Returns:
        WillContext with all entities and derived flags
    """
    context = WillContext()
    
    # Build will maker
    context.will_maker = WillMaker.from_dict(payload.get('will_maker', {}))
    
    # Build partner if applicable
    relationship_status = context.will_maker.relationship_status
    context.has_partner = relationship_status in ['married', 'de_facto']
    
    if context.has_partner:
        context.partner = Partner.from_dict(payload.get('partner', {}))
    
    # Separation details
    if relationship_status == 'separated':
        context.separation = payload.get('separation', {})
    
    # Build children
    if payload.get('has_children'):
        children_data = payload.get('children', [])
        context.children = [Child.from_dict(c) for c in children_data]
        context.has_children = len(context.children) > 0
        context.has_minor_children = any(
            c.is_expected_to_be_minor_at_death for c in context.children
        )
    
    # Build other dependants
    dependants_data = payload.get('dependants', {})
    if dependants_data.get('has_other_dependants'):
        other_deps = dependants_data.get('other_dependants', [])
        context.other_dependants = [Dependant.from_dict(d) for d in other_deps]
    
    # Build executors
    executors_data = payload.get('executors', {})
    executor_mode = executors_data.get('mode', '')
    
    if executor_mode == 'partner_only' and context.partner:
        context.executors = [Executor(
            full_name=context.partner.full_name,
            relationship='partner',
            address=context.partner.address,
            phone=context.partner.phone,
            email=context.partner.email
        )]
    elif executor_mode in ['one', 'two_joint', 'two_joint_and_several']:
        primary = executors_data.get('primary', [])
        context.executors = [Executor.from_dict(e) for e in primary]
    
    # Build backup executors
    backup_data = executors_data.get('backup', {})
    backup_mode = backup_data.get('mode', '')
    
    if backup_mode == 'partner' and context.partner:
        context.backup_executors = [Executor(
            full_name=context.partner.full_name,
            relationship='partner',
            address=context.partner.address
        )]
    elif backup_mode in ['one', 'two_joint', 'two_joint_and_several']:
        backup_list = backup_data.get('list', [])
        context.backup_executors = [Executor.from_dict(e) for e in backup_list]
    
    # Build guardians
    guardianship_data = payload.get('guardianship', {})
    if context.has_minor_children and guardianship_data.get('appoint_guardian'):
        context.guardian = Guardian.from_dict(guardianship_data.get('guardian', {}))
        context.has_guardianship = True
        
        backup_guardian_data = guardianship_data.get('backup_guardian', {})
        if backup_guardian_data and backup_guardian_data.get('full_name'):
            context.backup_guardian = Guardian.from_dict(backup_guardian_data)
    
    # Build beneficiaries and extract specific gifts/residue
    beneficiaries_data = payload.get('beneficiaries', [])
    context.beneficiaries = [
        Beneficiary.from_dict(b, i) for i, b in enumerate(beneficiaries_data)
    ]
    context.beneficiary_count = len(context.beneficiaries)
    
    # Extract specific gifts and residue beneficiaries
    for b in context.beneficiaries:
        if b.gift_role == 'specific_cash':
            context.specific_gifts.append(SpecificGift(
                beneficiary_id=b.id,
                beneficiary_name=b.full_name,
                gift_type='cash',
                cash_amount=b.cash_amount
            ))
            context.has_specific_gifts = True
        elif b.gift_role == 'specific_item':
            context.specific_gifts.append(SpecificGift(
                beneficiary_id=b.id,
                beneficiary_name=b.full_name,
                gift_type='item',
                item_description=b.item_description
            ))
            context.has_specific_gifts = True
        elif b.gift_role == 'residue':
            context.residue_beneficiaries.append(ResidueBeneficiary(
                beneficiary_id=b.id,
                beneficiary_name=b.full_name,
                share_percent=b.residue_share_percent
            ))
        
        if b.percentage is not None:
            context.percentage_sum += b.percentage
    
    context.has_residue_scheme = len(context.residue_beneficiaries) > 0
    context.has_percentages = context.percentage_sum > 0
    
    # Distribution settings
    distribution_data = payload.get('distribution', {})
    context.distribution_scheme = distribution_data.get('scheme', '')
    
    survivorship_data = payload.get('survivorship', {})
    context.survivorship_days = survivorship_data.get('days', 30)
    
    substitution_data = payload.get('substitution', {})
    context.substitution_rule = substitution_data.get('rule', '')
    context.has_substitution = bool(context.substitution_rule)
    
    if context.substitution_rule == 'to_alternate_beneficiary':
        context.alternate_beneficiary_id = substitution_data.get('alternate_beneficiary_id')
        context.has_alternate_beneficiary = True
        # Find alternate beneficiary name
        for b in context.beneficiaries:
            if b.id == context.alternate_beneficiary_id:
                context.alternate_beneficiary_name = b.full_name
                break
    
    # Minor trusts
    minor_trusts_data = payload.get('minor_trusts', {})
    if minor_trusts_data.get('enabled'):
        context.minor_trusts_enabled = True
        context.minor_trusts_vesting_age = minor_trusts_data.get('vesting_age', 18)
        context.minor_trusts_trustee_mode = minor_trusts_data.get('trustee_mode', '')
        
        if context.minor_trusts_trustee_mode == 'named_trustee':
            trustee_data = minor_trusts_data.get('trustee', {})
            context.minor_trusts_trustee = Executor.from_dict(trustee_data)
        
        # Determine if minor trusts clause should appear
        context.has_minor_trusts = (
            context.has_minor_children or 
            any(b.gift_role in ['residue', 'percentage_only'] for b in context.beneficiaries)
        )
    
    # Optional toggles
    toggles_data = payload.get('toggles', {})
    
    # Funeral wishes
    funeral_data = toggles_data.get('funeral', {})
    if funeral_data.get('enabled'):
        context.funeral_enabled = True
        context.has_funeral_wishes = True
        context.funeral_preference = funeral_data.get('preference', '')
        context.funeral_notes = funeral_data.get('notes', '')
    
    # Digital assets
    digital_assets_data = toggles_data.get('digital_assets', {})
    if digital_assets_data.get('enabled'):
        context.digital_assets_enabled = True
        context.has_digital_assets = True
        context.digital_assets_authority = digital_assets_data.get('authority', False)
        context.digital_assets_categories = digital_assets_data.get('categories', [])
        context.digital_assets_instructions_location = digital_assets_data.get('instructions_location', '')
    
    # Pets
    pets_data = toggles_data.get('pets', {})
    if pets_data.get('enabled'):
        context.pets_enabled = True
        context.has_pets = True
        context.pets_count = pets_data.get('count', 0)
        context.pets_summary = pets_data.get('summary', '')
        context.pets_carer_mode = pets_data.get('care_person_mode', '')
        context.pets_cash_gift = pets_data.get('cash_gift')
        
        if context.pets_carer_mode == 'select_beneficiary':
            care_beneficiary_id = pets_data.get('care_beneficiary_id')
            for b in context.beneficiaries:
                if b.id == care_beneficiary_id:
                    context.pets_carer_name = b.full_name
                    context.pets_carer_address = b.address
                    break
        elif context.pets_carer_mode == 'new_person':
            carer_data = pets_data.get('carer', {})
            context.pets_carer_name = carer_data.get('full_name', '')
            context.pets_carer_address = Address.from_dict(carer_data.get('address', {}))
    
    # Business interests
    business_data = toggles_data.get('business', {})
    if business_data.get('enabled'):
        context.business_enabled = True
        context.has_business_interests = True
        interests_data = business_data.get('interests', [])
        context.business_interests = [
            BusinessInterest.from_dict(i, context.beneficiaries) 
            for i in interests_data
        ]
    
    # Exclusions
    exclusion_data = toggles_data.get('exclusion', {})
    if exclusion_data.get('enabled'):
        context.exclusion_enabled = True
        context.has_exclusions = True
        exclusions_list = exclusion_data.get('exclusions', [])
        context.exclusions = [Exclusion.from_dict(e) for e in exclusions_list]
    
    # Life sustaining treatment
    life_sustaining_data = toggles_data.get('life_sustaining', {})
    if life_sustaining_data.get('enabled'):
        context.life_sustaining_enabled = True
        context.has_life_sustaining_statement = True
        context.life_sustaining_template = life_sustaining_data.get('template', '')
        context.life_sustaining_values = life_sustaining_data.get('values', [])
    
    # Assets overview
    context.assets = payload.get('assets', {})
    
    # Declarations
    declarations_data = payload.get('declarations', {})
    context.intended_signing_date = declarations_data.get('intended_signing_date')
    
    # Final derived counts
    context.executor_count = len(context.executors)
    
    return context
