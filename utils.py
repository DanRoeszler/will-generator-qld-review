"""
Utility functions for formatting, hashing, and text processing.
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


def format_full_name(name_parts: Dict[str, str]) -> str:
    """
    Format a full name from components.
    
    Args:
        name_parts: Dict with title, first_name, middle_names, last_name, suffix
    
    Returns:
        Formatted full name string
    """
    parts = []
    if name_parts.get('title'):
        parts.append(name_parts['title'])
    if name_parts.get('first_name'):
        parts.append(name_parts['first_name'])
    if name_parts.get('middle_names'):
        parts.append(name_parts['middle_names'])
    if name_parts.get('last_name'):
        parts.append(name_parts['last_name'])
    if name_parts.get('suffix'):
        parts.append(name_parts['suffix'])
    
    return ' '.join(parts)


def format_address(address: Dict[str, str]) -> str:
    """
    Format a structured address into a single line.
    
    Args:
        address: Dict with street, suburb, state, postcode
    
    Returns:
        Formatted address string
    """
    if not address:
        return ''
    
    parts = []
    if address.get('street'):
        parts.append(address['street'])
    if address.get('suburb'):
        parts.append(address['suburb'])
    if address.get('state'):
        parts.append(address['state'])
    if address.get('postcode'):
        parts.append(address['postcode'])
    
    return ', '.join(parts)


def format_address_multiline(address: Dict[str, str]) -> str:
    """
    Format a structured address into multiple lines.
    
    Args:
        address: Dict with street, suburb, state, postcode
    
    Returns:
        Formatted multi-line address string
    """
    if not address:
        return ''
    
    lines = []
    if address.get('street'):
        lines.append(address['street'])
    
    line2_parts = []
    if address.get('suburb'):
        line2_parts.append(address['suburb'])
    if address.get('state'):
        line2_parts.append(address['state'])
    if address.get('postcode'):
        line2_parts.append(address['postcode'])
    
    if line2_parts:
        lines.append(' '.join(line2_parts))
    
    return '\n'.join(lines)


def format_date(date_value: Any) -> str:
    """
    Format a date value into a standard string.
    
    Args:
        date_value: Date string, datetime object, or dict with year/month/day
    
    Returns:
        Formatted date string (DD Month YYYY)
    """
    if date_value is None:
        return ''
    
    if isinstance(date_value, datetime):
        return date_value.strftime('%d %B %Y')
    
    if isinstance(date_value, dict):
        try:
            dt = datetime(
                int(date_value['year']),
                int(date_value['month']),
                int(date_value['day'])
            )
            return dt.strftime('%d %B %Y')
        except (KeyError, ValueError, TypeError):
            return str(date_value)
    
    # Try parsing ISO format
    if isinstance(date_value, str):
        try:
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime('%d %B %Y')
        except ValueError:
            pass
        
        # Try YYYY-MM-DD format
        try:
            dt = datetime.strptime(date_value, '%Y-%m-%d')
            return dt.strftime('%d %B %Y')
        except ValueError:
            pass
    
    return str(date_value)


def format_currency(amount: float, currency: str = '$') -> str:
    """
    Format a numeric amount as currency.
    
    Args:
        amount: Numeric amount
        currency: Currency symbol
    
    Returns:
        Formatted currency string
    """
    if amount is None:
        return ''
    
    try:
        num = float(amount)
        if num == int(num):
            return f'{currency}{int(num):,}'
        return f'{currency}{num:,.2f}'
    except (ValueError, TypeError):
        return str(amount)


def format_percentage(value: float) -> str:
    """
    Format a numeric value as percentage.
    
    Args:
        value: Numeric percentage (e.g., 50 for 50%)
    
    Returns:
        Formatted percentage string
    """
    if value is None:
        return ''
    
    try:
        num = float(value)
        if num == int(num):
            return f'{int(num)}%'
        return f'{num:.2f}%'
    except (ValueError, TypeError):
        return str(value)


def calculate_sha256(data: bytes) -> str:
    """
    Calculate SHA256 hash of data.
    
    Args:
        data: Bytes to hash
    
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(data).hexdigest()


def short_hash(full_hash: str, length: int = 16) -> str:
    """
    Get a shortened version of a hash for display.
    
    Args:
        full_hash: Full hash string
        length: Number of characters to return
    
    Returns:
        Shortened hash string
    """
    if not full_hash:
        return ''
    return full_hash[:length]


def escape_text(text: str) -> str:
    """
    Escape special characters in text for safe PDF rendering.
    
    Args:
        text: Input text
    
    Returns:
        Escaped text safe for ReportLab
    """
    if not text:
        return ''
    
    # ReportLab uses XML-like escaping for special characters
    replacements = [
        ('&', '&amp;'),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('"', '&quot;'),
        ("'", '&apos;'),
    ]
    
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    
    return result


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing HTML tags and limiting length.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ''
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Limit length
    text = text[:max_length]
    
    # Strip whitespace
    text = text.strip()
    
    return text


def number_to_words(n: int) -> str:
    """
    Convert a number to words (for will documents).
    
    Args:
        n: Integer number
    
    Returns:
        Number in words
    """
    if n == 0:
        return 'zero'
    
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
    teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 
             'sixteen', 'seventeen', 'eighteen', 'nineteen']
    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
    
    def convert_less_than_thousand(num):
        if num == 0:
            return ''
        elif num < 10:
            return ones[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + ('' if num % 10 == 0 else '-' + ones[num % 10])
        else:
            return ones[num // 100] + ' hundred' + ('' if num % 100 == 0 else ' and ' + convert_less_than_thousand(num % 100))
    
    if n < 1000:
        return convert_less_than_thousand(n)
    elif n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        result = convert_less_than_thousand(thousands) + ' thousand'
        if remainder > 0:
            result += ' ' + convert_less_than_thousand(remainder)
        return result
    else:
        return str(n)  # Fallback for very large numbers


def ordinal(n: int) -> str:
    """
    Convert a number to its ordinal form.
    
    Args:
        n: Integer number
    
    Returns:
        Ordinal string (1st, 2nd, 3rd, etc.)
    """
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def is_minor_at_date(dob: Any, reference_date: Optional[datetime] = None) -> bool:
    """
    Determine if a person with given DOB would be a minor at a reference date.
    
    Args:
        dob: Date of birth (string or datetime)
        reference_date: Date to check against (defaults to now)
    
    Returns:
        True if person would be under 18 at reference date
    """
    if reference_date is None:
        reference_date = datetime.utcnow()
    
    birth_date = None
    if isinstance(dob, datetime):
        birth_date = dob
    elif isinstance(dob, str):
        try:
            birth_date = datetime.fromisoformat(dob.replace('Z', '+00:00'))
        except ValueError:
            try:
                birth_date = datetime.strptime(dob, '%Y-%m-%d')
            except ValueError:
                return False
    
    if birth_date is None:
        return False
    
    # Calculate age
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    return age < 18


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
    
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def get_brisbane_time() -> datetime:
    """
    Get current time in Brisbane timezone.
    
    Returns:
        Datetime in Australia/Brisbane timezone
    """
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('Australia/Brisbane'))


def format_brisbane_datetime(dt: Optional[datetime] = None) -> str:
    """
    Format datetime in Brisbane timezone.
    
    Args:
        dt: Datetime to format (defaults to now)
    
    Returns:
        Formatted datetime string
    """
    if dt is None:
        dt = get_brisbane_time()
    else:
        from zoneinfo import ZoneInfo
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        dt = dt.astimezone(ZoneInfo('Australia/Brisbane'))
    
    return dt.strftime('%d %B %Y at %I:%M %p %Z')
