"""
Normalize an incoming agent playbook into markdown text.

Sources supported:
- "paste":  pasted plain text          → stripped + returned
- "pdf":    raw PDF bytes              → pypdf text extraction
- "gdoc":   Google Doc URL or doc id   → Google Docs API export

Returns markdown text. The caller writes it to playbooks/<id>.md.
"""
import os
import re
import io


def ingest_paste(text):
    return (text or "").strip()


def ingest_pdf(pdf_bytes):
    """Extract text from a PDF blob using pypdf."""
    if not pdf_bytes:
        return ""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf not installed; run pip install pypdf") from e
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n\n".join(p for p in parts if p)
    return text.strip()


_GDOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def _extract_gdoc_id(url_or_id):
    if not url_or_id:
        return None
    s = url_or_id.strip()
    m = _GDOC_ID_RE.search(s)
    if m:
        return m.group(1)
    # Already an ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", s):
        return s
    return None


def ingest_gdoc(url_or_id):
    """Fetch a Google Doc as plain text using the existing token.json credentials."""
    doc_id = _extract_gdoc_id(url_or_id)
    if not doc_id:
        raise ValueError("Could not parse Google Doc id from input. Paste a doc URL or doc id.")
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError as e:
        raise RuntimeError("Google client libs not installed") from e

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    token_path = os.path.join(project_root, "token.json")
    if not os.path.isfile(token_path):
        raise RuntimeError(
            "token.json not found. The Google Doc fetcher needs the existing OAuth token. "
            "Make sure the doc is shared with the account that owns token.json (or 'anyone with the link can view')."
        )
    creds = Credentials.from_authorized_user_file(token_path)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    # Export as plain text via Drive API (works for Google Docs, requires read access)
    data = drive.files().export(fileId=doc_id, mimeType="text/plain").execute()
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace").strip()
    return str(data).strip()


def ingest(source_type, payload):
    """Dispatch by source_type. Returns markdown string."""
    if source_type == "paste":
        return ingest_paste(payload)
    if source_type == "pdf":
        return ingest_pdf(payload)
    if source_type == "gdoc":
        return ingest_gdoc(payload)
    raise ValueError(f"Unknown source_type: {source_type}")
