"""
Trainee-facing routes: agency-scoped landing page + agency-scoped APIs.

  GET  /train/<agency_slug>                   — setup screen, requires ?code=
  GET  /api/companies?agency=<slug>&code=...  — list of published scripts for that agency
  GET  /api/playbook/<id>?agency=<slug>&code=  — markdown of the agent playbook
"""
import logging

from flask import Blueprint, request, render_template, jsonify, abort

import auth
import script_store

logger = logging.getLogger(__name__)

trainee_bp = Blueprint("trainee", __name__)


def _require_trainee_access():
    agency_slug = request.values.get("agency") or request.view_args.get("agency_slug")
    code = request.values.get("code")
    if not auth.trainee_access_ok(agency_slug, code):
        return None, jsonify({"error": "invalid agency or access code"}), 403
    return agency_slug, None, None


@trainee_bp.route("/train/<agency_slug>")
def training_setup(agency_slug):
    code = request.args.get("code")
    if not auth.trainee_access_ok(agency_slug, code):
        return render_template("trainee_locked.html", agency_slug=agency_slug), 403
    m = auth.get_manager_by_agency_slug(agency_slug)
    return render_template(
        "trainee_setup.html",
        agency_slug=agency_slug,
        agency_name=m["agency_name"],
        access_code=code,
    )


@trainee_bp.route("/api/companies")
def api_companies():
    agency_slug = request.args.get("agency")
    code = request.args.get("code")
    if not auth.trainee_access_ok(agency_slug, code):
        return jsonify({"error": "invalid agency or access code"}), 403
    scripts = script_store.list_scripts_for_agency(agency_slug, published_only=True)
    return jsonify({
        "companies": [
            {
                "id": s.get("id"),
                "name": s.get("display_company") or s.get("name") or s.get("id"),
                "description": s.get("description", ""),
            }
            for s in scripts
        ]
    })


@trainee_bp.route("/api/playbook/<company_id>")
def api_playbook(company_id):
    agency_slug = request.args.get("agency")
    code = request.args.get("code")
    if not auth.trainee_access_ok(agency_slug, code):
        return jsonify({"error": "invalid agency or access code"}), 403
    if not script_store.is_company_in_agency(company_id, agency_slug):
        abort(404)
    md = script_store.read_playbook(company_id)
    if md is None:
        return jsonify({"markdown": "", "available": False})
    return jsonify({"markdown": md, "available": True})
