from cleaner import (
    clean_case_number,
    clean_email,
    clean_honorific,
    clean_record,
    clean_role,
    extract_honorific_from_name,
    normalize_department,
)


def test_clean_case_number():
    assert clean_case_number("PF202408262") == "PF-2024-08262"
    assert clean_case_number("PF-202408262") == "PF-2024-08262"
    assert clean_case_number("PF-2024-08262") == "PF-2024-08262"


def test_clean_email():
    assert clean_email("rharris @ example .com") == "rharris@example.com"
    assert clean_email("jdoe@example.com") == "jdoe@example.com"


def test_clean_role():
    assert clean_role("probation officer") == "Probation Officer"
    assert clean_role("PROBATION OFFICER") == "Probation Officer"
    assert clean_role("Probation Officer") == "Probation Officer"


def test_normalize_department():
    assert normalize_department("Probate & Family Court") == "Probate & Family Court"
    assert normalize_department("probate and family court") == "Probate & Family Court"
    assert normalize_department("PFC") == "Probate & Family Court"
    assert normalize_department("BMC") == "Boston Municipal Court"
    assert normalize_department("Superior Court") == "Superior Court"


def test_clean_honorific():
    assert clean_honorific("Hon") == "Hon."
    assert clean_honorific("Honor") == "Hon."
    assert clean_honorific("hon.") == "Hon."
    assert clean_honorific("Doctor") == "Dr."
    assert clean_honorific("dr") == "Dr."
    assert clean_honorific("unknown") == ""
    assert clean_honorific("") == ""


def test_extract_honorific_from_name():
    assert extract_honorific_from_name("Hon. Robert") == ("Hon.", "Robert")
    assert extract_honorific_from_name("Doctor Jane") == ("Dr.", "Jane")
    assert extract_honorific_from_name("Robert") == ("", "Robert")


def test_clean_record_combined_name():
    record = {
        "case_number": "",
        "honorific": "",
        "first_name": "",
        "last_name": "",
        "full_name": "Larry Simmons",
        "role": "",
        "department": "",
        "email": "",
        "status": "ZZZZ",
    }
    cleaned = clean_record(record)
    assert cleaned["first_name"] == "Larry"
    assert cleaned["last_name"] == "Simmons"
    assert cleaned["status"] == "inactive"
