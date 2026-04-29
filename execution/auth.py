"""
Auth helpers for the manager backend.

managers.json shape:
[
  {
    "agency_slug": "ao-globe-life",
    "agency_name": "AO / Globe Life",
    "email": "edwin@brandedfeel.com",
    "password_hash": "<bcrypt>",
    "trainee_access_code": "ABCD-1234",
    "created_at": "..."
  }
]

Script ownership is read directly off scripts/<id>.json's `agency_slug` field —
never duplicated here, so no sync issues.
"""
import os
import json
import secrets
import string
from functools import wraps
from datetime import datetime, timezone

import bcrypt
from flask import session, redirect, url_for, request, jsonify

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANAGERS_PATH = os.path.join(PROJECT_ROOT, "managers.json")


def _read_managers():
    if not os.path.isfile(MANAGERS_PATH):
        return []
    with open(MANAGERS_PATH, "r") as f:
        return json.load(f)


def _write_managers(managers):
    tmp = MANAGERS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(managers, f, indent=2)
    os.replace(tmp, MANAGERS_PATH)


def get_manager_by_email(email):
    if not email:
        return None
    for m in _read_managers():
        if m.get("email", "").lower() == email.lower():
            return m
    return None


def get_manager_by_agency_slug(slug):
    if not slug:
        return None
    for m in _read_managers():
        if m.get("agency_slug") == slug:
            return m
    return None


def verify_password(plain, password_hash):
    if not plain or not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_access_code():
    """8-char alphanumeric code, hyphenated for readability: ABCD-EFGH."""
    alphabet = string.ascii_uppercase + string.digits
    raw = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def add_manager(email, agency_slug, agency_name, password):
    """Append a new manager to managers.json. Returns the new record."""
    managers = _read_managers()
    if any(m.get("email", "").lower() == email.lower() for m in managers):
        raise ValueError(f"Manager with email {email} already exists")
    if any(m.get("agency_slug") == agency_slug for m in managers):
        raise ValueError(f"Agency slug '{agency_slug}' already taken")
    record = {
        "agency_slug": agency_slug,
        "agency_name": agency_name,
        "email": email,
        "password_hash": hash_password(password),
        "trainee_access_code": generate_access_code(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    managers.append(record)
    _write_managers(managers)
    return record


def update_manager(email, **fields):
    """Update one manager record by email. Whitelisted fields only."""
    allowed = {"trainee_access_code", "agency_name"}
    managers = _read_managers()
    for i, m in enumerate(managers):
        if m.get("email", "").lower() == email.lower():
            for k, v in fields.items():
                if k in allowed:
                    m[k] = v
            managers[i] = m
            _write_managers(managers)
            return m
    raise ValueError(f"No manager with email {email}")


def current_manager():
    """Return the currently logged-in manager record, or None."""
    email = session.get("manager_email")
    if not email:
        return None
    return get_manager_by_email(email)


def require_manager(view):
    """Decorator: require a logged-in manager."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        m = current_manager()
        if not m:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "auth required"}), 401
            return redirect(url_for("manager.login"))
        return view(*args, **kwargs)
    return wrapper


def require_company_owner(view):
    """Decorator: require logged-in manager AND that <company_id> path arg belongs to them."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        m = current_manager()
        if not m:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "auth required"}), 401
            return redirect(url_for("manager.login"))
        company_id = kwargs.get("company_id")
        if company_id and company_id not in (m.get("company_ids") or []):
            return jsonify({"error": "not your company"}), 403
        return view(*args, **kwargs)
    return wrapper


def trainee_access_ok(agency_slug, code):
    """For the trainee URL: verify slug + code combo."""
    m = get_manager_by_agency_slug(agency_slug)
    if not m:
        return False
    return secrets.compare_digest(
        (m.get("trainee_access_code") or ""), (code or "")
    )
