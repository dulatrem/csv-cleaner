"""
Cleaning functions for messy court personnel records.

Each function handles exactly one cleaning task and takes/returns plain
strings, so they can be composed and unit-tested independently. clean_record()
ties them together to turn one messy row (dict) into a cleaned row (dict).
"""

import re

import pandas as pd

# Canonical department names, keyed by a normalized form (lowercase, "and"
# instead of "&", collapsed whitespace) so lookups are forgiving of the
# variants/abbreviations produced by messy input.
DEPARTMENT_ALIASES = {
    "district court": "District Court",
    "superior court": "Superior Court",
    "juvenile court": "Juvenile Court",
    "boston municipal court": "Boston Municipal Court",
    "bmc": "Boston Municipal Court",
    "probate and family court": "Probate & Family Court",
    "pfc": "Probate & Family Court",
}

# The only valid role values in clean output.
ROLE_CANONICAL = [
    "Probation Officer",
    "Assistant Probation Officer",
    "Chief Probation Officer",
    "Office Clerk",
    "Office Manager",
]

# Canonical honorifics, keyed by lowercase spelling variant.
HONORIFIC_MAP = {
    "hon": "Hon.",
    "honor": "Hon.",
    "hon.": "Hon.",
    "dr": "Dr.",
    "doctor": "Dr.",
    "dr.": "Dr.",
}

# Matches a known honorific variant glued onto the front of a name, followed
# by whitespace and the rest of the name, e.g. "Hon. Robert" or "Honor David".
# Longer variants ("honor", "doctor") are listed before their shorter
# prefixes ("hon", "dr") so they aren't cut short by the alternation.
_HONORIFIC_PREFIX_RE = re.compile(
    r"^\s*(honor|hon\.?|doctor|dr\.?)\s+(?=\S)", re.IGNORECASE
)


def _to_str(value):
    """Coerce a possibly-NaN/None cell value (e.g. from pandas) to a string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def clean_case_number(value):
    """Normalize a case number to the canonical "PF-####-#####" format."""
    # Strip whitespace, drop any/all dashes, and uppercase first so we're
    # working from a consistent "PF" + 9 digits string regardless of where
    # dashes were originally placed (or missing).
    digits_only = value.strip().replace("-", "").upper()
    prefix, digits = digits_only[:2], digits_only[2:]
    year_part, seq_part = digits[:4], digits[4:9]
    return f"{prefix}-{year_part}-{seq_part}"


def clean_email(value):
    """Strip stray whitespace out of an email address and lowercase it."""
    return re.sub(r"\s+", "", value).lower()


def clean_role(value):
    """Match a role string (any case/spacing) to its canonical spelling."""
    # Collapse whitespace and lowercase so "PROBATION  OFFICER" and
    # "probation officer" both normalize to the same lookup key.
    normalized = re.sub(r"\s+", " ", value.strip()).lower()
    role_lookup = {role.lower(): role for role in ROLE_CANONICAL}
    return role_lookup.get(normalized, value.strip())


def normalize_department(value):
    """Match a department string (alias/abbreviation/casing) to its canonical name."""
    normalized = value.lower().replace("&", "and")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return DEPARTMENT_ALIASES.get(normalized, value)


def clean_honorific(value):
    """Match an honorific column value to its canonical spelling, or "" if unknown."""
    normalized = value.lower().strip()
    return HONORIFIC_MAP.get(normalized, "")


def extract_honorific_from_name(name):
    """
    Detect an honorific glued onto the front of a name string.

    Returns (canonical_honorific, remaining_name) if a known variant
    ("Hon", "Hon.", "Honor", "Dr", "Dr.", "Doctor") is found at the start of
    the name, followed by the rest of the name. Returns ("", name) otherwise.
    """
    match = _HONORIFIC_PREFIX_RE.match(name)
    if not match:
        return "", name

    token = match.group(1).rstrip(".").lower()
    honorific = HONORIFIC_MAP.get(token, "")
    if not honorific:
        return "", name

    remaining_name = name[match.end():].strip()
    return honorific, remaining_name


def clean_record(row):
    """
    Clean one messy record (dict) into a canonical record (dict).

    Expects `row` to have (at least) the keys: case_number, honorific,
    first_name, last_name, full_name, role, department, email, status.
    """
    case_number = clean_case_number(_to_str(row.get("case_number")))
    email = clean_email(_to_str(row.get("email")))

    full_name = _to_str(row.get("full_name")).strip()
    first_name = _to_str(row.get("first_name")).strip()
    last_name = _to_str(row.get("last_name")).strip()

    # Names may arrive as a single combined "full_name" column instead of
    # separate first/last columns. An honorific can be glued onto the front
    # of either form, so check for it on the raw name text *before*
    # splitting full_name -- otherwise a glued honorific (e.g. "Hon. Robert
    # Smith") would get mistaken for the first name once full_name is split.
    name_source = full_name if (full_name and not first_name) else first_name

    extracted_honorific, remaining_name = extract_honorific_from_name(name_source)
    if extracted_honorific:
        honorific = extracted_honorific
        name_source = remaining_name
    else:
        honorific = clean_honorific(_to_str(row.get("honorific")))

    if full_name and not first_name:
        # Split the (honorific-stripped) full name on the first space.
        name_parts = name_source.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
    else:
        first_name = name_source

    role = clean_role(_to_str(row.get("role")))
    department = normalize_department(_to_str(row.get("department")))

    # "ZZZZ" is a corrupted stand-in for "inactive"; anything else is kept
    # as-is (just lowercased) since "active"/"inactive" are already valid.
    raw_status = _to_str(row.get("status")).strip()
    status = "inactive" if raw_status == "ZZZZ" else raw_status.lower()

    return {
        "case_number": case_number,
        "honorific": honorific,
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "department": department,
        "email": email,
        "status": status,
    }
