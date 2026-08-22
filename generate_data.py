"""
Generates synthetic messy court personnel data for testing a data cleaner.

Step 1 generates clean, canonical records and saves them to data/clean_truth.csv.
Step 2 derives a corrupted copy of the same records (varied field-level messiness)
and saves it to data/messy_input.csv, so the cleaner's output can be diffed
against the clean truth.
"""

import random

import pandas as pd
from faker import Faker

fake = Faker()

NUM_RECORDS = 1000

DEPARTMENTS = [
    "District Court",
    "Superior Court",
    "Juvenile Court",
    "Boston Municipal Court",
    "Probate & Family Court",
]

ROLES = [
    "Probation Officer",
    "Assistant Probation Officer",
    "Chief Probation Officer",
    "Office Clerk",
    "Office Manager",
]

# Mostly empty (70%), otherwise "Hon." or "Dr."
HONORIFICS = ["", "", "", "", "", "", "Hon.", "Hon.", "Dr.", "Dr."]

# Department abbreviations used only during corruption (step 2)
DEPARTMENT_ABBREVIATIONS = {
    "Boston Municipal Court": "BMC",
    "Probate & Family Court": "PFC",
}


def generate_clean_records(n):
    """Build n clean canonical records as a list of dicts."""
    records = []
    for _ in range(n):
        case_number = f"PF-2024-{random.randint(0, 99999):05d}"
        honorific = random.choice(HONORIFICS)
        first_name = fake.first_name()
        last_name = fake.last_name()
        role = random.choice(ROLES)
        department = random.choice(DEPARTMENTS)
        email = f"{first_name[0].lower()}{last_name.lower()}@example.com"
        # Mostly active (85%), sometimes inactive (15%)
        status = random.choices(["active", "inactive"], weights=[85, 15])[0]

        records.append(
            {
                "case_number": case_number,
                "honorific": honorific,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "department": department,
                "email": email,
                "status": status,
            }
        )
    return records


def corrupt_case_number(case_number):
    """Randomly strip or misplace the dashes in the case number."""
    roll = random.random()
    if roll < 0.15:
        # Remove all dashes: "PF2024#####"
        return case_number.replace("-", "")
    elif roll < 0.30:
        # Drop only the second dash: "PF-2024#####"
        first_dash = case_number.find("-")
        return case_number[: first_dash + 1] + case_number[first_dash + 1 :].replace("-", "")
    return case_number


def corrupt_honorific_spelling(honorific):
    """Vary the honorific's spelling away from the canonical form."""
    if honorific == "Hon." and random.random() < 0.5:
        return random.choice(["Hon", "Honor"])
    if honorific == "Dr." and random.random() < 0.5:
        return random.choice(["Dr", "Doctor"])
    return honorific


def corrupt_role(role):
    """Randomly vary the casing/spacing of the role string."""
    roll = random.random()
    if roll < 0.15:
        return role.lower()
    elif roll < 0.30:
        return role.upper()
    elif roll < 0.40:
        # Extra internal spacing
        return "  ".join(role.split(" "))
    return role


def corrupt_department(department):
    """Randomly vary department spelling, casing, or abbreviate it."""
    roll = random.random()
    abbreviation = DEPARTMENT_ABBREVIATIONS.get(department)

    if abbreviation and roll < 0.15:
        return abbreviation
    elif roll < 0.30:
        return department.replace("&", "and")
    elif roll < 0.40:
        return department.lower()
    elif roll < 0.50:
        return department.upper()
    return department


def corrupt_email(email):
    """Randomly insert stray spaces around the @ and the final dot."""
    if random.random() < 0.15:
        email = email.replace("@", " @ ")
        email = email.replace(".com", " .com")
    return email


def corrupt_status(status):
    """Randomly mangle 'inactive' into 'ZZZZ'."""
    if status == "inactive" and random.random() < 0.4:
        return "ZZZZ"
    return status


def generate_messy_records(clean_records):
    """Derive a corrupted copy of clean_records with varied, independent field mess."""
    messy_records = []
    for clean in clean_records:
        row = dict(clean)

        row["case_number"] = corrupt_case_number(row["case_number"])
        row["role"] = corrupt_role(row["role"])
        row["department"] = corrupt_department(row["department"])
        row["email"] = corrupt_email(row["email"])
        row["status"] = corrupt_status(row["status"])

        # Vary honorific spelling before it potentially gets folded into the name
        honorific = corrupt_honorific_spelling(row["honorific"])
        row["honorific"] = honorific

        row["full_name"] = ""

        if honorific and random.random() < 0.3:
            # Move honorific into the name field, e.g. first_name -> "Hon. Robert"
            row["first_name"] = f"{honorific} {row['first_name']}"
            row["honorific"] = ""

        if random.random() < 0.25:
            # Combine first/last into a single full_name column, blank out the split columns
            row["full_name"] = f"{row['first_name']} {row['last_name']}".strip()
            row["first_name"] = ""
            row["last_name"] = ""

        messy_records.append(row)
    return messy_records


def main():
    clean_records = generate_clean_records(NUM_RECORDS)
    clean_df = pd.DataFrame(clean_records)
    clean_df.to_csv("data/clean_truth.csv", index=False)

    messy_records = generate_messy_records(clean_records)
    messy_df = pd.DataFrame(
        messy_records,
        columns=[
            "case_number",
            "honorific",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "department",
            "email",
            "status",
        ],
    )
    messy_df.to_csv("data/messy_input.csv", index=False)

    print(f"Generated {len(clean_records)} records.")
    print("Wrote data/clean_truth.csv")
    print("Wrote data/messy_input.csv")


if __name__ == "__main__":
    main()
