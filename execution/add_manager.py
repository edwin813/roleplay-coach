"""Interactive CLI to seed managers.json. Run from project root:

    python execution/add_manager.py
"""
import getpass
import re
import sys

from auth import add_manager


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "agency"


def main():
    print("\n--- Add Manager ---\n")
    email = input("Manager email: ").strip()
    if not email or "@" not in email:
        print("Invalid email."); sys.exit(1)

    agency_name = input("Agency display name (e.g. 'AO / Globe Life'): ").strip()
    if not agency_name:
        print("Agency name required."); sys.exit(1)

    suggested = slugify(agency_name)
    slug_input = input(f"Agency URL slug [{suggested}]: ").strip() or suggested
    slug = slugify(slug_input)

    pwd = getpass.getpass("Password (will be bcrypt-hashed): ")
    pwd2 = getpass.getpass("Confirm password: ")
    if pwd != pwd2:
        print("Passwords don't match."); sys.exit(1)
    if len(pwd) < 8:
        print("Password must be at least 8 characters."); sys.exit(1)

    try:
        record = add_manager(email=email, agency_slug=slug, agency_name=agency_name, password=pwd)
    except ValueError as e:
        print(f"Error: {e}"); sys.exit(1)

    print("\n✅ Manager created.")
    print(f"  Email:        {record['email']}")
    print(f"  Agency:       {record['agency_name']}")
    print(f"  Trainee URL:  /train/{record['agency_slug']}?code={record['trainee_access_code']}")
    print(f"  Login at:     /manager/login")


if __name__ == "__main__":
    main()
