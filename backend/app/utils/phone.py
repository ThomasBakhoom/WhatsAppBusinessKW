"""Phone number utilities for Kuwait (+965) and international numbers."""

import phonenumbers
from phonenumbers import PhoneNumberFormat


def normalize_phone(phone: str, default_region: str = "KW") -> str:
    """
    Normalize a phone number to E.164 format.

    Examples:
        "96599887766" -> "+96599887766"
        "99887766" -> "+96599887766"
        "+96599887766" -> "+96599887766"
    """
    try:
        parsed = phonenumbers.parse(phone, default_region)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number: {phone}")
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException as e:
        raise ValueError(f"Cannot parse phone number '{phone}': {e}") from e


def is_kuwaiti_number(phone: str) -> bool:
    """Check if a phone number is a Kuwaiti number (+965)."""
    try:
        parsed = phonenumbers.parse(phone, "KW")
        return parsed.country_code == 965
    except phonenumbers.NumberParseException:
        return False


def format_display(phone: str) -> str:
    """Format a phone number for display (e.g., +965 9988 7766)."""
    try:
        parsed = phonenumbers.parse(phone, "KW")
        return phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    except phonenumbers.NumberParseException:
        return phone
