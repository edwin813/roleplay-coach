"""
Read/write helpers for scripts/<id>.json (the AI Roleplay Configs).

Every script may carry these tenant fields:
    agency_slug:      "ao-globe-life"   # which manager/agency owns it
    owner_email:      "edwin@..."       # who created/last edited
    display_company:  "AO / Globe Life — Plus Lead"
    published:        true              # only published scripts are visible to trainees

Plus the runtime-required fields (id, persona.sponsors[], objections.{difficulty}[]).
"""
import os
import json
import re
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
PLAYBOOKS_DIR = os.path.join(PROJECT_ROOT, "playbooks")


def _ensure_dirs():
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(PLAYBOOKS_DIR, exist_ok=True)


def slugify_company_id(name):
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "company"


def list_all_scripts():
    """Return every script JSON with its company_id added in."""
    _ensure_dirs()
    out = []
    if not os.path.isdir(SCRIPTS_DIR):
        return out
    for fn in sorted(os.listdir(SCRIPTS_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(SCRIPTS_DIR, fn), "r") as f:
                data = json.load(f)
            data.setdefault("id", fn[:-5])
            out.append(data)
        except Exception:
            continue
    return out


def list_scripts_for_agency(agency_slug, published_only=False):
    if not agency_slug:
        return []
    out = []
    for s in list_all_scripts():
        if s.get("agency_slug") != agency_slug:
            continue
        if published_only and not s.get("published"):
            continue
        out.append(s)
    return out


def get_script(company_id):
    path = os.path.join(SCRIPTS_DIR, f"{company_id}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def write_script(script):
    """Atomic write of a script JSON. Requires `id`."""
    _ensure_dirs()
    company_id = script.get("id")
    if not company_id:
        raise ValueError("script missing 'id'")
    path = os.path.join(SCRIPTS_DIR, f"{company_id}.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(script, f, indent=2)
    os.replace(tmp, path)
    return path


def reserve_company_id(display_company):
    """Pick a unique company_id slug. Auto-suffix on collision."""
    base = slugify_company_id(display_company)
    candidate = base
    n = 2
    while os.path.isfile(os.path.join(SCRIPTS_DIR, f"{candidate}.json")):
        candidate = f"{base}_{n}"
        n += 1
    return candidate


def stub_script(company_id, agency_slug, display_company, owner_email):
    """Minimal valid script the runtime can load. Manager edits objections + persona later."""
    return {
        "id": company_id,
        "agency_slug": agency_slug,
        "owner_email": owner_email,
        "display_company": display_company,
        "name": display_company,
        "description": "",
        "published": False,
        "persona": {
            "sponsors": [{"name": "Sample", "relationship": "friend"}],
            "moods": ["curious", "skeptical", "busy"],
            "pain_points": ["time", "cost", "trust"],
            "remembers_sponsorship_probability": 0.5,
        },
        "objections": {
            "beginner": [],
            "intermediate": [],
            "advanced": [],
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def is_company_in_agency(company_id, agency_slug):
    s = get_script(company_id)
    return bool(s and s.get("agency_slug") == agency_slug)


# ---- Playbook (the agent script trainees recite) ----

def write_playbook(company_id, markdown_text, source_type, source_ref, manager_email):
    _ensure_dirs()
    md_path = os.path.join(PLAYBOOKS_DIR, f"{company_id}.md")
    meta_path = os.path.join(PLAYBOOKS_DIR, f"{company_id}.meta.json")
    with open(md_path, "w") as f:
        f.write(markdown_text or "")
    meta = {
        "source_type": source_type,
        "source_ref": source_ref,
        "manager_email": manager_email,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def read_playbook(company_id):
    md_path = os.path.join(PLAYBOOKS_DIR, f"{company_id}.md")
    if not os.path.isfile(md_path):
        return None
    with open(md_path, "r") as f:
        return f.read()


def read_playbook_meta(company_id):
    meta_path = os.path.join(PLAYBOOKS_DIR, f"{company_id}.meta.json")
    if not os.path.isfile(meta_path):
        return {}
    with open(meta_path, "r") as f:
        return json.load(f)
