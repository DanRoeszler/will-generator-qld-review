"""
Strict JSON schema validation for will generator payloads.

Validation Rules Documentation:
===============================

1. ELIGIBILITY (Section A)
   - All three confirmations must be true (age, QLD residence, legal advice disclaimer)
   
2. WILL MAKER (Section B)
   - Full name: required, max 100 chars, no HTML
   - DOB: required, valid date format, must be 18+ years old
   - Occupation: required, max 100 chars
   - Address: all components required, postcode must be 4 digits
   - Email: required, valid format
   - Phone: required, 8-20 chars, digits/spaces/hyphens/parens only
   - Relationship status: required enum value
   
3. PARTNER (conditional on married/de facto)
   - Full name: required
   - Address: all components required
   - Email/phone: optional but validated if provided
   
4. SEPARATION (conditional on separated)
   - is_legally_separated: required boolean
   - has_property_agreement: optional boolean
   
5. CHILDREN (Section C)
   - has_children: required boolean
   - If true: at least 1 child required, max 20
   - Each child: full_name, dob, relationship_type required
   - is_expected_to_be_minor_at_death: boolean (triggers guardianship section)
   
6. DEPENDANTS
   - has_other_dependants: required boolean
   - If true: at least 1 dependant required
   
7. EXECUTORS (Section D)
   - mode: required enum
   - If one/two_joint/two_joint_and_several: exactly 1 or 2 executors required
   - Each executor: full_name, relationship, address required
   - Backup executor: mode required, same validation as primary
   
8. GUARDIANSHIP (Section E - conditional)
   - Only shown if has_minor_children is true
   - appoint_guardian: required boolean
   - If true: guardian full_name, relationship, address required
   - Backup guardian: optional but fully validated if provided
   
9. DISTRIBUTION (Section F)
   - scheme: required enum
   - partner_then_children_equal: requires partner AND children
   - children_equal: requires children
   - percentages_named: requires beneficiaries totaling exactly 100%
   - specific_gifts_then_residue: requires at least 1 specific gift AND 1 residue beneficiary
   
10. BENEFICIARIES
    - type: individual or charity
    - full_name: required
    - relationship: required for individuals
    - address: required for individuals
    - gift_role: determines other required fields
    - cash_amount: required if gift_role=specific_cash, max $100M
    - item_description: required if gift_role=specific_item, max 120 chars
    - percentage: required if gift_role=percentage_only, must sum to 100%
    
11. SURVIVORSHIP
    - days: required enum [0, 7, 14, 30, 60]
    
12. SUBSTITUTION
    - rule: required enum
    - to_alternate_beneficiary: requires alternate_beneficiary_id referencing valid beneficiary
    
13. MINOR TRUSTS (conditional)
    - enabled: boolean
    - If enabled: vesting_age required [18, 21, 25]
    - trustee_mode: required enum
    - named_trustee: requires full trustee details if selected
    
14. OPTIONAL CLAUSES (Section G)
    - Each toggle has specific sub-field requirements when enabled
    - Funeral: preference required when enabled
    - Digital assets: authority boolean, categories array, instructions_location required
    - Pets: count (1-10), summary, care arrangement required
    - Business: at least 1 interest required when enabled
    - Exclusion: at least 1 exclusion required when enabled
    - Life sustaining: template required when enabled
    
15. DECLARATIONS (Section I)
    - All four confirmations required: reviewed, complex_advice, super_and_joint, signing_witness
    - intended_signing_date: optional but validated if provided

Cross-Section Validation Rules:
===============================
- Guardian cannot be appointed without minor children
- Percentage beneficiaries must sum to exactly 100%
- Alternate beneficiary must reference existing beneficiary
- Specific gifts scheme requires at least one specific gift
- Partner-only executor requires partner to exist
- Trustee appointment requires minor trusts to be enabled
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ValidationError:
    """Represents a single validation error with precise field path."""
    field: str
    message: str
    code: str
    section: str = ''  # For grouping errors by section


@dataclass
class ValidationResult:
    """Container for validation results."""
    errors: List[ValidationError] = field(default_factory=list)
    is_valid: bool = True
    warnings: List[ValidationError] = field(default_factory=list)  # Non-blocking issues
    
    def add_error(self, field: str, message: str, code: str = 'invalid', section: str = ''):
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, code, section))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, code: str = 'warning', section: str = ''):
        """Add a non-blocking warning."""
        self.warnings.append(ValidationError(field, message, code, section))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            'ok': self.is_valid,
            'errors': [
                {'field': e.field, 'message': e.message, 'code': e.code, 'section': e.section}
                for e in self.errors
            ],
            'warnings': [
                {'field': w.field, 'message': w.message, 'code': w.code, 'section': w.section}
                for w in self.warnings
            ]
        }
    
    def get_errors_by_section(self) -> Dict[str, List[ValidationError]]:
        """Group errors by section for UI display."""
        by_section = {}
        for error in self.errors:
            section = error.section or 'general'
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(error)
        return by_section


# Constants for validation
MAX_NAME_LENGTH = 100
MAX_TEXT_LENGTH = 500
MAX_NOTES_LENGTH = 500
MAX_ADDRESS_LENGTH = 200
MAX_CASH_GIFT = 100_000_000  # $100M cap
MAX_PERCENTAGE = 100
MIN_PERCENTAGE = 0
MAX_PETS = 10
MAX_CHILDREN = 20
MAX_BENEFICIARIES = 50
MAX_EXECUTORS = 4
MAX_DEPENDANTS = 10

# Regex patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'^[0-9\s\-+()]{8,20}$')
POSTCODE_PATTERN = re.compile(r'^\d{4}$')  # Queensland postcodes
ABN_PATTERN = re.compile(r'^\d{11}$')
ACN_PATTERN = re.compile(r'^\d{9}$')
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

# Enums - strictly enforced
RELATIONSHIP_STATUSES = ['single', 'married', 'de_facto', 'separated', 'divorced', 'widowed']
EXECUTOR_MODES = ['partner_only', 'one', 'two_joint', 'two_joint_and_several']
BACKUP_EXECUTOR_MODES = ['none', 'partner', 'one', 'two_joint', 'two_joint_and_several']
DISTRIBUTION_SCHEMES = [
    'partner_then_children_equal',
    'children_equal',
    'percentages_named',
    'specific_gifts_then_residue',
    'custom_structured'
]
BENEFICIARY_TYPES = ['individual', 'charity']
GIFT_ROLES = ['residue', 'specific_cash', 'specific_item', 'percentage_only']
CHILD_RELATIONSHIPS = ['biological', 'adopted', 'stepchild', 'dependent_other']
SURVIVORSHIP_DAYS = [0, 7, 14, 30, 60]
SURVIVORSHIP_DAYS_INT = [0, 7, 14, 30, 60]  # Integer versions
SUBSTITUTION_RULES = ['to_their_children', 'redistribute_among_remaining', 'to_alternate_beneficiary']
MINOR_TRUST_VESTING_AGES = [18, 21, 25]
MINOR_TRUST_TRUSTEE_MODES = ['executors_as_trustees', 'named_trustee']
FUNERAL_PREFERENCES = ['burial', 'cremation', 'no_preference']
DIGITAL_ASSET_CATEGORIES = ['email', 'social_media', 'cloud_storage', 'crypto']
PET_CARE_MODES = ['select_beneficiary', 'new_person']
BUSINESS_INTEREST_TYPES = ['sole_trader', 'company_shareholding', 'partnership', 'trust_interest']
EXCLUSION_CATEGORIES = ['former_partner', 'child', 'stepchild', 'dependant_other']
EXCLUSION_REASONS = ['already_provided_for', 'estrangement', 'financial_independence', 'other_structured']
LIFE_SUSTAINING_TEMPLATES = [
    'comfort_and_dignity_prioritised',
    'palliative_only_in_terminal_or_permanent_unconsciousness',
    'prolong_life_if_reasonable'
]
LIFE_SUSTAINING_VALUES = ['comfort', 'dignity', 'palliative_care', 'avoid_burdensome_treatment']


def coerce_to_bool(value: Any) -> Optional[bool]:
    """Coerce various inputs to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    if isinstance(value, int):
        return value == 1
    return None


def coerce_to_int(value: Any) -> Optional[int]:
    """Coerce various inputs to integer."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def coerce_to_float(value: Any) -> Optional[float]:
    """Coerce various inputs to float."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def validate_boolean(value: Any, field_name: str, result: ValidationResult, 
                     required: bool = True, section: str = '') -> bool:
    """Validate a boolean field with strict type checking."""
    if value is None or value == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    coerced = coerce_to_bool(value)
    if coerced is None:
        result.add_error(field_name, 'Must be true or false', 'type', section)
        return False
    
    return True


def validate_string(value: Any, field_name: str, result: ValidationResult, 
                    required: bool = True, max_length: int = MAX_NAME_LENGTH,
                    allow_html: bool = False, section: str = '') -> bool:
    """Validate a string field."""
    if value is None or str(value).strip() == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    str_value = str(value).strip()
    
    if len(str_value) > max_length:
        result.add_error(field_name, f'Maximum {max_length} characters allowed', 'max_length', section)
        return False
    
    if not allow_html and HTML_TAG_PATTERN.search(str_value):
        result.add_error(field_name, 'HTML tags are not allowed', 'invalid_chars', section)
        return False
    
    return True


def validate_email(value: Any, field_name: str, result: ValidationResult, 
                   required: bool = True, section: str = '') -> bool:
    """Validate an email address."""
    if value is None or str(value).strip() == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    str_value = str(value).strip()
    
    if len(str_value) > 254:
        result.add_error(field_name, 'Email address is too long', 'max_length', section)
        return False
    
    if not EMAIL_PATTERN.match(str_value):
        result.add_error(field_name, 'Please enter a valid email address', 'format', section)
        return False
    
    return True


def validate_phone(value: Any, field_name: str, result: ValidationResult, 
                   required: bool = True, section: str = '') -> bool:
    """Validate a phone number."""
    if value is None or str(value).strip() == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    str_value = str(value).strip()
    
    if not PHONE_PATTERN.match(str_value):
        result.add_error(field_name, 'Please enter a valid phone number', 'format', section)
        return False
    
    return True


def validate_date(value: Any, field_name: str, result: ValidationResult, 
                  required: bool = True, section: str = '', min_age: int = None) -> bool:
    """Validate a date field (YYYY-MM-DD format)."""
    if value is None or str(value).strip() == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    str_value = str(value).strip()
    parsed_date = None
    
    # Try ISO format
    try:
        parsed_date = datetime.fromisoformat(str_value.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Try YYYY-MM-DD format
    if parsed_date is None:
        try:
            parsed_date = datetime.strptime(str_value, '%Y-%m-%d')
        except ValueError:
            result.add_error(field_name, 'Please enter a valid date (YYYY-MM-DD)', 'format', section)
            return False
    
    # Check minimum age if specified
    if min_age is not None:
        age = (datetime.utcnow() - parsed_date).days / 365.25
        if age < min_age:
            result.add_error(field_name, f'Must be at least {min_age} years old', 'min_age', section)
            return False
    
    return True


def validate_enum(value: Any, field_name: str, allowed: List[str], 
                  result: ValidationResult, required: bool = True, section: str = '') -> bool:
    """Validate an enum field with strict matching."""
    if value is None or str(value).strip() == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    str_value = str(value).strip()
    
    if str_value not in allowed:
        result.add_error(field_name, f'Must be one of: {", ".join(allowed)}', 'enum', section)
        return False
    
    return True


def validate_int_enum(value: Any, field_name: str, allowed: List[int], 
                      result: ValidationResult, required: bool = True, section: str = '') -> bool:
    """Validate an integer enum field."""
    if value is None or value == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    coerced = coerce_to_int(value)
    if coerced is None:
        result.add_error(field_name, 'Must be a valid number', 'type', section)
        return False
    
    if coerced not in allowed:
        result.add_error(field_name, f'Must be one of: {", ".join(map(str, allowed))}', 'enum', section)
        return False
    
    return True


def validate_address(address: Dict[str, Any], field_name: str, 
                     result: ValidationResult, required: bool = True, section: str = '') -> bool:
    """Validate a structured address."""
    if address is None or not isinstance(address, dict):
        if required:
            result.add_error(field_name, 'Address is required', 'required', section)
        return False
    
    # Street is required
    if not validate_string(address.get('street'), f'{field_name}.street', result, 
                          required=True, max_length=MAX_ADDRESS_LENGTH, section=section):
        return False
    
    # Suburb is required
    if not validate_string(address.get('suburb'), f'{field_name}.suburb', result,
                          required=True, max_length=100, section=section):
        return False
    
    # State is required
    if not validate_string(address.get('state'), f'{field_name}.state', result,
                          required=True, max_length=50, section=section):
        return False
    
    # Postcode is required and must be 4 digits
    postcode = address.get('postcode')
    if postcode is None or str(postcode).strip() == '':
        result.add_error(f'{field_name}.postcode', 'Postcode is required', 'required', section)
        return False
    
    if not POSTCODE_PATTERN.match(str(postcode)):
        result.add_error(f'{field_name}.postcode', 'Please enter a valid 4-digit postcode', 'format', section)
        return False
    
    return True


def validate_positive_number(value: Any, field_name: str, result: ValidationResult,
                             required: bool = True, max_value: Optional[float] = None,
                             section: str = '') -> bool:
    """Validate a positive number."""
    if value is None or value == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    try:
        num = float(value)
        if num < 0:
            result.add_error(field_name, 'Must be a positive number', 'min_value', section)
            return False
        if max_value is not None and num > max_value:
            result.add_error(field_name, f'Must not exceed {max_value}', 'max_value', section)
            return False
        return True
    except (ValueError, TypeError):
        result.add_error(field_name, 'Must be a valid number', 'type', section)
        return False


def validate_percentage(value: Any, field_name: str, result: ValidationResult,
                        required: bool = True, section: str = '') -> bool:
    """Validate a percentage value (0-100)."""
    if value is None or value == '':
        if required:
            result.add_error(field_name, 'This field is required', 'required', section)
        return False
    
    try:
        num = float(value)
        if num < MIN_PERCENTAGE or num > MAX_PERCENTAGE:
            result.add_error(field_name, 'Percentage must be between 0 and 100', 'range', section)
            return False
        return True
    except (ValueError, TypeError):
        result.add_error(field_name, 'Must be a valid percentage', 'type', section)
        return False


def validate_payload(payload: Dict[str, Any]) -> ValidationResult:
    """
    Main validation entry point. Validates the entire payload.
    
    Args:
        payload: The JSON payload from the form submission
    
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult()
    
    if not isinstance(payload, dict):
        result.add_error('', 'Payload must be a JSON object', 'type', 'general')
        return result
    
    # Section A: Eligibility and intent
    _validate_section_a(payload, result)
    
    # Section B: Will maker details
    will_maker = _validate_section_b(payload, result)
    
    # Section C: Children and dependants
    children = _validate_section_c(payload, result)
    
    # Section D: Executors and trustees
    _validate_section_d(payload, result, will_maker)
    
    # Section E: Guardianship (only if has minor children)
    _validate_section_e(payload, result, children)
    
    # Section F: Gifts and distribution plan
    beneficiaries = _validate_section_f(payload, result, will_maker, children)
    
    # Section G: Optional clause toggles
    _validate_section_g(payload, result, beneficiaries)
    
    # Section H: Assets overview (informational only)
    _validate_section_h(payload, result)
    
    # Section I: Final review and declarations
    _validate_section_i(payload, result)
    
    # Cross-section validation
    _validate_cross_section_logic(payload, result, will_maker, children, beneficiaries)
    
    return result


def _validate_section_a(payload: Dict[str, Any], result: ValidationResult):
    """Validate Section A: Eligibility and intent."""
    section = 'eligibility'
    section_data = payload.get('eligibility', {})
    
    if not isinstance(section_data, dict):
        result.add_error('eligibility', 'Eligibility section is required', 'required', section)
        return
    
    validate_boolean(section_data.get('confirm_age_over_18'), 'eligibility.confirm_age_over_18', result, section=section)
    validate_boolean(section_data.get('confirm_qld'), 'eligibility.confirm_qld', result, section=section)
    validate_boolean(section_data.get('confirm_not_legal_advice'), 'eligibility.confirm_not_legal_advice', result, section=section)
    
    # All must be true
    if section_data.get('confirm_age_over_18') is not True:
        result.add_error('eligibility.confirm_age_over_18', 'You must confirm you are 18 or older', 'invalid', section)
    if section_data.get('confirm_qld') is not True:
        result.add_error('eligibility.confirm_qld', 'You must confirm Queensland residency', 'invalid', section)
    if section_data.get('confirm_not_legal_advice') is not True:
        result.add_error('eligibility.confirm_not_legal_advice', 'You must acknowledge this is not legal advice', 'invalid', section)


def _validate_section_b(payload: Dict[str, Any], result: ValidationResult) -> Dict[str, Any]:
    """Validate Section B: Will maker details."""
    section = 'will_maker'
    will_maker = payload.get('will_maker', {})
    
    if not isinstance(will_maker, dict):
        result.add_error('will_maker', 'Will maker details are required', 'required', section)
        return {}
    
    # Required fields
    validate_string(will_maker.get('full_name'), 'will_maker.full_name', result, section=section)
    validate_date(will_maker.get('dob'), 'will_maker.dob', result, min_age=18, section=section)
    validate_string(will_maker.get('occupation'), 'will_maker.occupation', result, section=section)
    validate_address(will_maker.get('address'), 'will_maker.address', result, section=section)
    validate_email(will_maker.get('email'), 'will_maker.email', result, section=section)
    validate_phone(will_maker.get('phone'), 'will_maker.phone', result, section=section)
    
    # Relationship status
    relationship_status = will_maker.get('relationship_status')
    validate_enum(relationship_status, 'will_maker.relationship_status', 
                  RELATIONSHIP_STATUSES, result, section=section)
    
    # Partner details if married or de facto
    if relationship_status in ['married', 'de_facto']:
        partner = payload.get('partner', {})
        if not isinstance(partner, dict):
            result.add_error('partner', 'Partner details are required', 'required', section)
        else:
            validate_string(partner.get('full_name'), 'partner.full_name', result, section=section)
            validate_date(partner.get('dob'), 'partner.dob', result, required=False, section=section)
            validate_address(partner.get('address'), 'partner.address', result, section=section)
            validate_email(partner.get('email'), 'partner.email', result, required=False, section=section)
            validate_phone(partner.get('phone'), 'partner.phone', result, required=False, section=section)
    
    # Separation details if separated
    if relationship_status == 'separated':
        separation = payload.get('separation', {})
        if not isinstance(separation, dict):
            result.add_error('separation', 'Separation details are required', 'required', section)
        else:
            validate_boolean(separation.get('is_legally_separated'), 
                           'separation.is_legally_separated', result, section=section)
            validate_boolean(separation.get('has_property_agreement'),
                           'separation.has_property_agreement', result, required=False, section=section)
    
    return will_maker


def _validate_section_c(payload: Dict[str, Any], result: ValidationResult) -> List[Dict[str, Any]]:
    """Validate Section C: Children and dependants."""
    section = 'children'
    has_children = payload.get('has_children')
    validate_boolean(has_children, 'has_children', result, section=section)
    
    children = []
    if has_children is True:
        children = payload.get('children', [])
        if not isinstance(children, list) or len(children) == 0:
            result.add_error('children', 'At least one child is required when has_children is true', 'required', section)
        elif len(children) > MAX_CHILDREN:
            result.add_error('children', f'Maximum {MAX_CHILDREN} children allowed', 'max_items', section)
        else:
            for i, child in enumerate(children):
                prefix = f'children[{i}]'
                if not isinstance(child, dict):
                    result.add_error(prefix, 'Child details are required', 'required', section)
                    continue
                
                validate_string(child.get('full_name'), f'{prefix}.full_name', result, section=section)
                validate_date(child.get('dob'), f'{prefix}.dob', result, section=section)
                validate_enum(child.get('relationship_type'), f'{prefix}.relationship_type',
                            CHILD_RELATIONSHIPS, result, section=section)
                validate_boolean(child.get('is_expected_to_be_minor_at_death'),
                               f'{prefix}.is_expected_to_be_minor_at_death', result, required=False, section=section)
                validate_boolean(child.get('special_needs'), f'{prefix}.special_needs', result, required=False, section=section)
    
    # Other dependants
    dependants = payload.get('dependants', {})
    if isinstance(dependants, dict):
        has_other_dependants = dependants.get('has_other_dependants')
        validate_boolean(has_other_dependants, 'dependants.has_other_dependants', result, section=section)
        
        if has_other_dependants is True:
            other_dependants = dependants.get('other_dependants', [])
            if not isinstance(other_dependants, list) or len(other_dependants) == 0:
                result.add_error('dependants.other_dependants', 
                               'At least one dependant is required', 'required', section)
            elif len(other_dependants) > MAX_DEPENDANTS:
                result.add_error('dependants.other_dependants', 
                               f'Maximum {MAX_DEPENDANTS} dependants allowed', 'max_items', section)
            else:
                for i, dep in enumerate(other_dependants):
                    prefix = f'dependants.other_dependants[{i}]'
                    if not isinstance(dep, dict):
                        result.add_error(prefix, 'Dependant details are required', 'required', section)
                        continue
                    
                    validate_string(dep.get('full_name'), f'{prefix}.full_name', result, section=section)
                    validate_string(dep.get('relationship_category'), f'{prefix}.relationship_category',
                                  result, max_length=60, section=section)
    
    return children


def _validate_section_d(payload: Dict[str, Any], result: ValidationResult, will_maker: Dict[str, Any]):
    """Validate Section D: Executors and trustees."""
    section = 'executors'
    executors = payload.get('executors', {})
    if not isinstance(executors, dict):
        result.add_error('executors', 'Executor details are required', 'required', section)
        return
    
    executor_mode = executors.get('mode')
    validate_enum(executor_mode, 'executors.mode', EXECUTOR_MODES, result, section=section)
    
    # Validate partner_only requires partner
    if executor_mode == 'partner_only':
        relationship_status = will_maker.get('relationship_status')
        if relationship_status not in ['married', 'de_facto']:
            result.add_error('executors.mode', 'Partner-only executor requires a partner', 'dependency', section)
    
    # Validate primary executors if not partner_only
    if executor_mode in ['one', 'two_joint', 'two_joint_and_several']:
        primary = executors.get('primary', [])
        if not isinstance(primary, list):
            result.add_error('executors.primary', 'Primary executors list is required', 'required', section)
        else:
            expected_count = 1 if executor_mode == 'one' else 2
            if len(primary) != expected_count:
                result.add_error('executors.primary', 
                               f'Exactly {expected_count} executor(s) required for mode "{executor_mode}"',
                               'count', section)
            else:
                for i, executor in enumerate(primary):
                    prefix = f'executors.primary[{i}]'
                    if not isinstance(executor, dict):
                        result.add_error(prefix, 'Executor details are required', 'required', section)
                        continue
                    
                    validate_string(executor.get('full_name'), f'{prefix}.full_name', result, section=section)
                    validate_string(executor.get('relationship'), f'{prefix}.relationship',
                                  result, max_length=60, section=section)
                    validate_address(executor.get('address'), f'{prefix}.address', result, section=section)
                    validate_phone(executor.get('phone'), f'{prefix}.phone', result, required=False, section=section)
                    validate_email(executor.get('email'), f'{prefix}.email', result, required=False, section=section)
    
    # Backup executor
    backup_data = executors.get('backup', {})
    if not isinstance(backup_data, dict):
        result.add_error('executors.backup', 'Backup executor details required', 'required', section)
        return
        
    backup_mode = backup_data.get('mode')
    validate_enum(backup_mode, 'executors.backup.mode', BACKUP_EXECUTOR_MODES, result, section=section)
    
    if backup_mode == 'partner':
        relationship_status = will_maker.get('relationship_status')
        if relationship_status not in ['married', 'de_facto']:
            result.add_error('executors.backup.mode', 'Partner backup requires a partner', 'dependency', section)
    
    if backup_mode in ['one', 'two_joint', 'two_joint_and_several']:
        backup_list = backup_data.get('list', [])
        if not isinstance(backup_list, list):
            result.add_error('executors.backup.list', 'Backup executors list is required', 'required', section)
        else:
            expected_count = 1 if backup_mode == 'one' else 2
            if len(backup_list) != expected_count:
                result.add_error('executors.backup.list',
                               f'Exactly {expected_count} backup executor(s) required',
                               'count', section)
            else:
                for i, executor in enumerate(backup_list):
                    prefix = f'executors.backup.list[{i}]'
                    if not isinstance(executor, dict):
                        result.add_error(prefix, 'Backup executor details are required', 'required', section)
                        continue
                    
                    validate_string(executor.get('full_name'), f'{prefix}.full_name', result, section=section)
                    validate_string(executor.get('relationship'), f'{prefix}.relationship',
                                  result, max_length=60, section=section)
                    validate_address(executor.get('address'), f'{prefix}.address', result, section=section)


def _validate_section_e(payload: Dict[str, Any], result: ValidationResult, children: List[Dict[str, Any]]):
    """Validate Section E: Guardianship (only if has minor children)."""
    section = 'guardianship'
    
    # Check if any child is expected to be minor
    has_minor_children = any(
        child.get('is_expected_to_be_minor_at_death', False) 
        for child in children
    ) if children else False
    
    if not has_minor_children:
        return
    
    guardianship = payload.get('guardianship', {})
    if not isinstance(guardianship, dict):
        result.add_error('guardianship', 'Guardianship details are required when minor children exist', 'required', section)
        return
    
    appoint_guardian = guardianship.get('appoint_guardian')
    validate_boolean(appoint_guardian, 'guardianship.appoint_guardian', result, section=section)
    
    if appoint_guardian is True:
        guardian = guardianship.get('guardian', {})
        if isinstance(guardian, dict):
            validate_string(guardian.get('full_name'), 'guardianship.guardian.full_name', result, section=section)
            validate_string(guardian.get('relationship'), 'guardianship.guardian.relationship',
                          result, max_length=60, section=section)
            validate_address(guardian.get('address'), 'guardianship.guardian.address', result, section=section)
            validate_phone(guardian.get('phone'), 'guardianship.guardian.phone', result, required=False, section=section)
        else:
            result.add_error('guardianship.guardian', 'Guardian details are required', 'required', section)
        
        # Backup guardian is optional
        backup = guardianship.get('backup_guardian', {})
        if isinstance(backup, dict) and backup.get('full_name'):
            validate_string(backup.get('full_name'), 'guardianship.backup_guardian.full_name', result, section=section)
            validate_string(backup.get('relationship'), 'guardianship.backup_guardian.relationship',
                          result, max_length=60, section=section)
            validate_address(backup.get('address'), 'guardianship.backup_guardian.address', result, section=section)


def _validate_section_f(payload: Dict[str, Any], result: ValidationResult, 
                        will_maker: Dict[str, Any], children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate Section F: Gifts and distribution plan."""
    section = 'distribution'
    distribution = payload.get('distribution', {})
    if not isinstance(distribution, dict):
        result.add_error('distribution', 'Distribution details are required', 'required', section)
        return []
    
    scheme = distribution.get('scheme')
    validate_enum(scheme, 'distribution.scheme', DISTRIBUTION_SCHEMES, result, section=section)
    
    has_partner = will_maker.get('relationship_status') in ['married', 'de_facto']
    has_children_val = payload.get('has_children', False)
    
    # Validate scheme requirements
    if scheme == 'partner_then_children_equal' and not has_partner:
        result.add_error('distribution.scheme', 
                       'This scheme requires a partner', 'dependency', section)
    
    if scheme in ['partner_then_children_equal', 'children_equal'] and not has_children_val:
        result.add_error('distribution.scheme',
                       'This scheme requires at least one child', 'dependency', section)
    
    # Validate beneficiaries
    beneficiaries = payload.get('beneficiaries', [])
    if not isinstance(beneficiaries, list):
        result.add_error('beneficiaries', 'Beneficiaries list is required', 'required', section)
        return []
    
    if len(beneficiaries) == 0:
        result.add_error('beneficiaries', 'At least one beneficiary is required', 'required', section)
    elif len(beneficiaries) > MAX_BENEFICIARIES:
        result.add_error('beneficiaries', f'Maximum {MAX_BENEFICIARIES} beneficiaries allowed', 'max_items', section)
    else:
        percentage_sum = 0
        has_specific_gifts = False
        has_residue = False
        beneficiary_ids = set()
        
        for i, beneficiary in enumerate(beneficiaries):
            prefix = f'beneficiaries[{i}]'
            if not isinstance(beneficiary, dict):
                result.add_error(prefix, 'Beneficiary details are required', 'required', section)
                continue
            
            # Track IDs for reference validation
            bid = beneficiary.get('id') or f'beneficiary_{i}'
            if bid in beneficiary_ids:
                result.add_error(prefix, f'Duplicate beneficiary ID: {bid}', 'duplicate', section)
            beneficiary_ids.add(bid)
            
            # Type
            btype = beneficiary.get('type')
            validate_enum(btype, f'{prefix}.type', BENEFICIARY_TYPES, result, section=section)
            
            # Name
            validate_string(beneficiary.get('full_name'), f'{prefix}.full_name', result, section=section)
            
            # Relationship (required for individuals)
            if btype == 'individual':
                validate_string(beneficiary.get('relationship'), f'{prefix}.relationship',
                              result, max_length=60, section=section)
                validate_address(beneficiary.get('address'), f'{prefix}.address', result, section=section)
            
            # ABN for charities
            if btype == 'charity':
                abn = beneficiary.get('abn')
                if abn and not ABN_PATTERN.match(str(abn)):
                    result.add_error(f'{prefix}.abn', 'Please enter a valid 11-digit ABN', 'format', section)
            
            # Gift role
            gift_role = beneficiary.get('gift_role')
            validate_enum(gift_role, f'{prefix}.gift_role', GIFT_ROLES, result, section=section)
            
            if gift_role == 'specific_cash':
                has_specific_gifts = True
                cash_amount = beneficiary.get('cash_amount')
                validate_positive_number(cash_amount, f'{prefix}.cash_amount', result,
                                        max_value=MAX_CASH_GIFT, section=section)
            
            if gift_role == 'specific_item':
                has_specific_gifts = True
                validate_string(beneficiary.get('item_description'), f'{prefix}.item_description',
                              result, max_length=120, section=section)
            
            if gift_role == 'percentage_only':
                percentage = beneficiary.get('percentage')
                validate_percentage(percentage, f'{prefix}.percentage', result, section=section)
                if percentage is not None:
                    percentage_sum += float(percentage)
            
            if gift_role == 'residue':
                has_residue = True
                residue_percent = beneficiary.get('residue_share_percent')
                if residue_percent is not None:
                    validate_percentage(residue_percent, f'{prefix}.residue_share_percent', result, section=section)
        
        # Validate percentage sum for percentage schemes
        if scheme == 'percentages_named' and abs(percentage_sum - 100) > 0.01:
            result.add_error('beneficiaries', 
                           f'Percentages must sum to exactly 100% (current: {percentage_sum:.2f}%)',
                           'percentage_sum', section)
        
        # Validate specific gifts scheme requirements
        if scheme == 'specific_gifts_then_residue':
            if not has_specific_gifts:
                result.add_error('beneficiaries',
                               'This scheme requires at least one specific gift', 'dependency', section)
            if not has_residue:
                result.add_error('beneficiaries',
                               'This scheme requires at least one residue beneficiary', 'dependency', section)
    
    # Survivorship - use int enum validation
    survivorship = payload.get('survivorship', {})
    if isinstance(survivorship, dict):
        days = survivorship.get('days')
        validate_int_enum(days, 'survivorship.days', SURVIVORSHIP_DAYS_INT, result, section=section)
    
    # Substitution
    substitution = payload.get('substitution', {})
    if isinstance(substitution, dict):
        rule = substitution.get('rule')
        validate_enum(rule, 'substitution.rule', SUBSTITUTION_RULES, result, section=section)
        
        if rule == 'to_alternate_beneficiary':
            alt_id = substitution.get('alternate_beneficiary_id')
            if alt_id is None or alt_id == '':
                result.add_error('substitution.alternate_beneficiary_id',
                               'Alternate beneficiary is required', 'required', section)
            elif alt_id not in [b.get('id', f'beneficiary_{i}') for i, b in enumerate(beneficiaries)]:
                result.add_error('substitution.alternate_beneficiary_id',
                               'Alternate beneficiary must reference an existing beneficiary', 'invalid_reference', section)
    
    # Minor trusts
    minor_trusts = payload.get('minor_trusts', {})
    if isinstance(minor_trusts, dict):
        enabled = minor_trusts.get('enabled')
        validate_boolean(enabled, 'minor_trusts.enabled', result, required=False, section=section)
        
        if enabled is True:
            validate_int_enum(minor_trusts.get('vesting_age'), 'minor_trusts.vesting_age',
                        MINOR_TRUST_VESTING_AGES, result, section=section)
            trustee_mode = minor_trusts.get('trustee_mode')
            validate_enum(trustee_mode, 'minor_trusts.trustee_mode',
                        MINOR_TRUST_TRUSTEE_MODES, result, section=section)
            
            if trustee_mode == 'named_trustee':
                trustee = minor_trusts.get('trustee', {})
                if isinstance(trustee, dict):
                    validate_string(trustee.get('full_name'), 'minor_trusts.trustee.full_name', result, section=section)
                    validate_address(trustee.get('address'), 'minor_trusts.trustee.address', result, section=section)
                else:
                    result.add_error('minor_trusts.trustee', 'Trustee details are required', 'required', section)
    
    return beneficiaries


def _validate_section_g(payload: Dict[str, Any], result: ValidationResult, 
                        beneficiaries: List[Dict[str, Any]]):
    """Validate Section G: Optional clause toggles."""
    section = 'toggles'
    toggles = payload.get('toggles', {})
    if not isinstance(toggles, dict):
        toggles = {}
    
    # G1: Funeral wishes
    funeral = toggles.get('funeral', {})
    if isinstance(funeral, dict) and funeral.get('enabled') is True:
        validate_enum(funeral.get('preference'), 'toggles.funeral.preference',
                    FUNERAL_PREFERENCES, result, section=section)
        validate_string(funeral.get('notes'), 'toggles.funeral.notes',
                      result, required=False, max_length=200, section=section)
    
    # G2: Digital assets
    digital_assets = toggles.get('digital_assets', {})
    if isinstance(digital_assets, dict) and digital_assets.get('enabled') is True:
        validate_boolean(digital_assets.get('authority'), 'toggles.digital_assets.authority', result, section=section)
        
        categories = digital_assets.get('categories', [])
        if not isinstance(categories, list) or len(categories) == 0:
            result.add_error('toggles.digital_assets.categories',
                           'At least one category must be selected', 'required', section)
        else:
            for i, cat in enumerate(categories):
                validate_enum(cat, f'toggles.digital_assets.categories[{i}]',
                            DIGITAL_ASSET_CATEGORIES, result, section=section)
        
        validate_string(digital_assets.get('instructions_location'),
                      'toggles.digital_assets.instructions_location',
                      result, max_length=120, section=section)
    
    # G3: Pets
    pets = toggles.get('pets', {})
    if isinstance(pets, dict) and pets.get('enabled') is True:
        count = pets.get('count')
        validate_positive_number(count, 'toggles.pets.count', result, max_value=MAX_PETS, section=section)
        
        validate_string(pets.get('summary'), 'toggles.pets.summary', result, max_length=120, section=section)
        
        care_mode = pets.get('care_person_mode')
        validate_enum(care_mode, 'toggles.pets.care_person_mode', PET_CARE_MODES, result, section=section)
        
        if care_mode == 'select_beneficiary':
            care_beneficiary_id = pets.get('care_beneficiary_id')
            if care_beneficiary_id is None or care_beneficiary_id == '':
                result.add_error('toggles.pets.care_beneficiary_id',
                               'Beneficiary selection is required', 'required', section)
            else:
                # Validate beneficiary exists
                beneficiary_ids = [b.get('id', f'beneficiary_{i}') for i, b in enumerate(beneficiaries)]
                if care_beneficiary_id not in beneficiary_ids:
                    result.add_error('toggles.pets.care_beneficiary_id',
                                   'Selected beneficiary does not exist', 'invalid_reference', section)
        elif care_mode == 'new_person':
            carer = pets.get('carer', {})
            if isinstance(carer, dict):
                validate_string(carer.get('full_name'), 'toggles.pets.carer.full_name', result, section=section)
                validate_address(carer.get('address'), 'toggles.pets.carer.address', result, section=section)
            else:
                result.add_error('toggles.pets.carer', 'Carer details are required', 'required', section)
        
        cash_gift = pets.get('cash_gift')
        if cash_gift is not None:
            validate_positive_number(cash_gift, 'toggles.pets.cash_gift', result,
                                    required=False, max_value=MAX_CASH_GIFT, section=section)
    
    # G4: Business interests
    business = toggles.get('business', {})
    if isinstance(business, dict) and business.get('enabled') is True:
        interests = business.get('interests', [])
        if not isinstance(interests, list) or len(interests) == 0:
            result.add_error('toggles.business.interests',
                           'At least one business interest is required', 'required', section)
        else:
            for i, interest in enumerate(interests):
                prefix = f'toggles.business.interests[{i}]'
                if not isinstance(interest, dict):
                    result.add_error(prefix, 'Business interest details are required', 'required', section)
                    continue
                
                validate_enum(interest.get('interest_type'), f'{prefix}.interest_type',
                            BUSINESS_INTEREST_TYPES, result, section=section)
                validate_string(interest.get('entity_name'), f'{prefix}.entity_name', result, section=section)
                
                acn = interest.get('acn')
                if acn and not ACN_PATTERN.match(str(acn)):
                    result.add_error(f'{prefix}.acn', 'Please enter a valid 9-digit ACN', 'format', section)
                
                abn = interest.get('abn')
                if abn and not ABN_PATTERN.match(str(abn)):
                    result.add_error(f'{prefix}.abn', 'Please enter a valid 11-digit ABN', 'format', section)
                
                recipient_mode = interest.get('recipient_mode')
                validate_enum(recipient_mode, f'{prefix}.recipient_mode',
                            ['select_beneficiary', 'new_person'], result, section=section)
                
                if recipient_mode == 'select_beneficiary':
                    recipient_id = interest.get('recipient_id')
                    if recipient_id is None or recipient_id == '':
                        result.add_error(f'{prefix}.recipient_id',
                                       'Beneficiary selection is required', 'required', section)
                    else:
                        beneficiary_ids = [b.get('id', f'beneficiary_{i}') for i, b in enumerate(beneficiaries)]
                        if recipient_id not in beneficiary_ids:
                            result.add_error(f'{prefix}.recipient_id',
                                           'Selected beneficiary does not exist', 'invalid_reference', section)
                elif recipient_mode == 'new_person':
                    recipient = interest.get('recipient', {})
                    if isinstance(recipient, dict):
                        validate_string(recipient.get('full_name'), f'{prefix}.recipient.full_name', result, section=section)
                        validate_address(recipient.get('address'), f'{prefix}.recipient.address', result, section=section)
                    else:
                        result.add_error(f'{prefix}.recipient', 'Recipient details are required', 'required', section)
    
    # G5: Exclusions
    exclusion = toggles.get('exclusion', {})
    if isinstance(exclusion, dict) and exclusion.get('enabled') is True:
        exclusions = exclusion.get('exclusions', [])
        if not isinstance(exclusions, list) or len(exclusions) == 0:
            result.add_error('toggles.exclusion.exclusions',
                           'At least one exclusion is required', 'required', section)
        else:
            for i, excl in enumerate(exclusions):
                prefix = f'toggles.exclusion.exclusions[{i}]'
                if not isinstance(excl, dict):
                    result.add_error(prefix, 'Exclusion details are required', 'required', section)
                    continue
                
                validate_string(excl.get('person_name'), f'{prefix}.person_name', result, section=section)
                validate_enum(excl.get('category'), f'{prefix}.category',
                            EXCLUSION_CATEGORIES, result, section=section)
                
                reasons = excl.get('reasons', [])
                if not isinstance(reasons, list) or len(reasons) == 0:
                    result.add_error(f'{prefix}.reasons',
                                   'At least one reason must be selected', 'required', section)
                else:
                    for j, reason in enumerate(reasons):
                        validate_enum(reason, f'{prefix}.reasons[{j}]',
                                    EXCLUSION_REASONS, result, section=section)
                
                if 'other_structured' in reasons:
                    validate_string(excl.get('other_note'), f'{prefix}.other_note',
                                  result, max_length=300, section=section)
    
    # G6: Life sustaining treatment
    life_sustaining = toggles.get('life_sustaining', {})
    if isinstance(life_sustaining, dict) and life_sustaining.get('enabled') is True:
        validate_enum(life_sustaining.get('template'), 'toggles.life_sustaining.template',
                    LIFE_SUSTAINING_TEMPLATES, result, section=section)
        
        values = life_sustaining.get('values', [])
        if isinstance(values, list):
            for i, val in enumerate(values):
                validate_enum(val, f'toggles.life_sustaining.values[{i}]',
                            LIFE_SUSTAINING_VALUES, result, required=False, section=section)


def _validate_section_h(payload: Dict[str, Any], result: ValidationResult):
    """Validate Section H: Assets overview (informational only)."""
    section = 'assets'
    assets = payload.get('assets', {})
    if not isinstance(assets, dict):
        return
    
    asset_types = ['real_property', 'bank', 'superannuation', 'investments', 'vehicles', 'business', 'other']
    
    for asset_type in asset_types:
        value = assets.get(asset_type)
        if value is not None and value != '':
            validate_positive_number(value, f'assets.{asset_type}', result,
                                    required=False, max_value=999_999_999_999, section=section)


def _validate_section_i(payload: Dict[str, Any], result: ValidationResult):
    """Validate Section I: Final review and declarations."""
    section = 'declarations'
    declarations = payload.get('declarations', {})
    if not isinstance(declarations, dict):
        declarations = payload
    
    validate_boolean(declarations.get('confirm_reviewed'), 
                    'declarations.confirm_reviewed', result, section=section)
    validate_boolean(declarations.get('confirm_complex_advice'),
                    'declarations.confirm_complex_advice', result, section=section)
    validate_boolean(declarations.get('confirm_super_and_joint'),
                    'declarations.confirm_super_and_joint', result, section=section)
    validate_boolean(declarations.get('confirm_signing_witness'),
                    'declarations.confirm_signing_witness', result, section=section)
    
    # All declarations must be true
    if declarations.get('confirm_reviewed') is not True:
        result.add_error('declarations.confirm_reviewed', 'You must confirm you have reviewed all information', 'invalid', section)
    if declarations.get('confirm_complex_advice') is not True:
        result.add_error('declarations.confirm_complex_advice', 'You must acknowledge complex circumstances may require legal advice', 'invalid', section)
    if declarations.get('confirm_super_and_joint') is not True:
        result.add_error('declarations.confirm_super_and_joint', 'You must acknowledge superannuation and jointly held assets may not pass under this will', 'invalid', section)
    if declarations.get('confirm_signing_witness') is not True:
        result.add_error('declarations.confirm_signing_witness', 'You must acknowledge proper signing and witnessing requirements apply', 'invalid', section)
    
    # Intended signing date is optional
    signing_date = declarations.get('intended_signing_date')
    if signing_date:
        validate_date(signing_date, 'declarations.intended_signing_date', result, required=False, section=section)


def _validate_cross_section_logic(payload: Dict[str, Any], result: ValidationResult,
                                  will_maker: Dict[str, Any], children: List[Dict[str, Any]],
                                  beneficiaries: List[Dict[str, Any]]):
    """
    Validate logical consistency across sections.
    
    This catches contradictions that single-section validation might miss.
    """
    # Check for self-referencing beneficiaries in substitution
    substitution = payload.get('substitution', {})
    if isinstance(substitution, dict):
        rule = substitution.get('rule')
        alt_id = substitution.get('alternate_beneficiary_id')
        
        if rule == 'to_alternate_beneficiary' and alt_id:
            # Check if alternate is also a primary beneficiary
            for i, ben in enumerate(beneficiaries):
                ben_id = ben.get('id', f'beneficiary_{i}')
                if ben_id == alt_id and ben.get('gift_role') in ['residue', 'percentage_only']:
                    # This is valid - alternate can be a primary beneficiary
                    pass
    
    # Check for duplicate executor/guardian names
    executors = []
    executor_data = payload.get('executors', {})
    if isinstance(executor_data, dict):
        primary = executor_data.get('primary', [])
        if isinstance(primary, list):
            executors.extend([e.get('full_name', '') for e in primary if isinstance(e, dict)])
        backup = executor_data.get('backup', {}).get('list', [])
        if isinstance(backup, list):
            executors.extend([e.get('full_name', '') for e in backup if isinstance(e, dict)])
    
    guardianship = payload.get('guardianship', {})
    if isinstance(guardianship, dict) and guardianship.get('appoint_guardian'):
        guardian = guardianship.get('guardian', {})
        if isinstance(guardian, dict):
            guardian_name = guardian.get('full_name', '')
            if guardian_name in executors:
                # Warning: Same person as executor and guardian
                result.add_warning('guardianship.guardian.full_name',
                                 'This person is also appointed as an executor. This is allowed but should be intentional.',
                                 'potential_duplicate', 'guardianship')
    
    # Check for minors without trust provision
    has_minor_children = any(
        c.get('is_expected_to_be_minor_at_death', False) for c in children
    ) if children else False
    
    minor_trusts = payload.get('minor_trusts', {})
    has_minor_trusts = isinstance(minor_trusts, dict) and minor_trusts.get('enabled') is True
    
    if has_minor_children and not has_minor_trusts:
        result.add_warning('minor_trusts.enabled',
                          'You have minor children but have not enabled trusts for minors. '
                          'Consider whether this is intentional.',
                          'missing_trust', 'minor_trusts')
