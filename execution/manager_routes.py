"""
Flask blueprint for the manager backend at /manager/*.

Routes:
  GET/POST  /manager/login                          login form
  POST      /manager/logout                         clear session
  GET       /manager/                               dashboard
  POST      /manager/rotate-code                    rotate trainee access code
  GET       /manager/company/new                    new-company upload form
  POST      /manager/company/new                    process upload, create stub script
  GET/POST  /manager/company/<id>/roleplay          edit AI Roleplay Config
  GET/POST  /manager/company/<id>/playbook          view/replace agent playbook
  POST      /manager/company/<id>/publish           toggle published flag
"""
import json
import logging

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
)

import auth
import script_store
import playbook_ingest
import playbook_extractor

logger = logging.getLogger(__name__)

manager_bp = Blueprint("manager", __name__, url_prefix="/manager")


# ---------- auth ----------

@manager_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        m = auth.get_manager_by_email(email)
        if not m or not auth.verify_password(password, m.get("password_hash")):
            flash("Invalid email or password.", "error")
            return render_template("manager/login.html"), 401
        session["manager_email"] = m["email"]
        return redirect(url_for("manager.dashboard"))
    return render_template("manager/login.html")


@manager_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("manager_email", None)
    return redirect(url_for("manager.login"))


# ---------- dashboard ----------

@manager_bp.route("/")
@auth.require_manager
def dashboard():
    m = auth.current_manager()
    scripts = script_store.list_scripts_for_agency(m["agency_slug"])
    trainee_url = url_for(
        "trainee.training_setup",
        agency_slug=m["agency_slug"],
        code=m["trainee_access_code"],
        _external=True,
    )
    return render_template(
        "manager/dashboard.html",
        manager=m,
        scripts=scripts,
        trainee_url=trainee_url,
    )


@manager_bp.route("/rotate-code", methods=["POST"])
@auth.require_manager
def rotate_code():
    m = auth.current_manager()
    new_code = auth.generate_access_code()
    auth.update_manager(m["email"], trainee_access_code=new_code)
    flash("Access code rotated. Re-share the new trainee URL.", "success")
    return redirect(url_for("manager.dashboard"))


# ---------- new company ----------

@manager_bp.route("/company/new", methods=["GET"])
@auth.require_manager
def new_company_form():
    return render_template("manager/new_company.html")


@manager_bp.route("/company/new", methods=["POST"])
@auth.require_manager
def new_company_submit():
    m = auth.current_manager()
    display_company = (request.form.get("display_company") or "").strip()
    source_type = (request.form.get("source_type") or "paste").strip()
    if not display_company:
        flash("Please give the company a display name.", "error")
        return redirect(url_for("manager.new_company_form"))

    # Pull payload by source type
    try:
        if source_type == "paste":
            text = request.form.get("paste_text") or ""
            markdown = playbook_ingest.ingest_paste(text)
            source_ref = "(pasted)"
        elif source_type == "pdf":
            pdf_file = request.files.get("pdf_file")
            if not pdf_file:
                flash("No PDF uploaded.", "error")
                return redirect(url_for("manager.new_company_form"))
            markdown = playbook_ingest.ingest_pdf(pdf_file.read())
            source_ref = pdf_file.filename or "(pdf)"
        elif source_type == "gdoc":
            url_or_id = (request.form.get("gdoc_url") or "").strip()
            markdown = playbook_ingest.ingest_gdoc(url_or_id)
            source_ref = url_or_id
        else:
            flash(f"Unknown upload type: {source_type}", "error")
            return redirect(url_for("manager.new_company_form"))
    except Exception as e:
        logger.exception("Ingest failed")
        flash(f"Could not read that file: {e}", "error")
        return redirect(url_for("manager.new_company_form"))

    if not markdown or len(markdown.strip()) < 20:
        flash("The script came through empty or too short. Try pasting it directly.", "error")
        return redirect(url_for("manager.new_company_form"))

    # Reserve a unique company_id slug, write the playbook, write a stub script
    company_id = script_store.reserve_company_id(display_company)
    script_store.write_playbook(
        company_id=company_id,
        markdown_text=markdown,
        source_type=source_type,
        source_ref=source_ref,
        manager_email=m["email"],
    )
    stub = script_store.stub_script(
        company_id=company_id,
        agency_slug=m["agency_slug"],
        display_company=display_company,
        owner_email=m["email"],
    )
    # Try to seed objections + persona from the playbook with Claude
    suggestion, note = playbook_extractor.suggest_roleplay_from_playbook(markdown)
    stub["persona"] = suggestion.get("persona") or stub["persona"]
    stub["objections"] = suggestion.get("objections") or stub["objections"]
    script_store.write_script(stub)

    flash(note, "info")
    return redirect(url_for("manager.edit_roleplay", company_id=company_id))


# ---------- edit roleplay config ----------

@manager_bp.route("/company/<company_id>/roleplay", methods=["GET", "POST"])
@auth.require_manager
def edit_roleplay(company_id):
    m = auth.current_manager()
    if not script_store.is_company_in_agency(company_id, m["agency_slug"]):
        abort(404)
    script = script_store.get_script(company_id)

    if request.method == "POST":
        raw_json = request.form.get("script_json") or ""
        try:
            edited = json.loads(raw_json)
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {e}", "error")
            return render_template(
                "manager/edit_roleplay.html",
                company_id=company_id,
                script_json=raw_json,
                script=script,
            )
        # Re-stamp tenancy fields server-side so the manager can't reassign ownership
        edited["id"] = company_id
        edited["agency_slug"] = m["agency_slug"]
        edited["owner_email"] = m["email"]
        # Preserve the previous published flag (publish has its own endpoint)
        edited["published"] = bool(script.get("published"))
        # Quick sanity check on the runtime contract
        persona = edited.get("persona") or {}
        sponsors = persona.get("sponsors") or []
        objections = edited.get("objections") or {}
        total_objs = sum(
            len(objections.get(d, []) or []) for d in ("beginner", "intermediate", "advanced")
        )
        if not sponsors:
            flash("persona.sponsors must have at least one entry.", "error")
            return render_template(
                "manager/edit_roleplay.html",
                company_id=company_id,
                script_json=raw_json,
                script=script,
            )
        if total_objs == 0:
            flash("Add at least one objection at any difficulty before saving.", "error")
            return render_template(
                "manager/edit_roleplay.html",
                company_id=company_id,
                script_json=raw_json,
                script=script,
            )
        script_store.write_script(edited)
        flash("Roleplay config saved.", "success")
        return redirect(url_for("manager.edit_roleplay", company_id=company_id))

    return render_template(
        "manager/edit_roleplay.html",
        company_id=company_id,
        script_json=json.dumps(script, indent=2),
        script=script,
    )


# ---------- view/replace playbook ----------

@manager_bp.route("/company/<company_id>/playbook", methods=["GET", "POST"])
@auth.require_manager
def edit_playbook(company_id):
    m = auth.current_manager()
    if not script_store.is_company_in_agency(company_id, m["agency_slug"]):
        abort(404)

    if request.method == "POST":
        source_type = (request.form.get("source_type") or "paste").strip()
        try:
            if source_type == "paste":
                markdown = playbook_ingest.ingest_paste(request.form.get("paste_text") or "")
                source_ref = "(pasted)"
            elif source_type == "pdf":
                pdf_file = request.files.get("pdf_file")
                if not pdf_file:
                    flash("No PDF uploaded.", "error")
                    return redirect(url_for("manager.edit_playbook", company_id=company_id))
                markdown = playbook_ingest.ingest_pdf(pdf_file.read())
                source_ref = pdf_file.filename or "(pdf)"
            elif source_type == "gdoc":
                url_or_id = (request.form.get("gdoc_url") or "").strip()
                markdown = playbook_ingest.ingest_gdoc(url_or_id)
                source_ref = url_or_id
            else:
                flash(f"Unknown upload type: {source_type}", "error")
                return redirect(url_for("manager.edit_playbook", company_id=company_id))
        except Exception as e:
            logger.exception("Replace playbook failed")
            flash(f"Could not read that file: {e}", "error")
            return redirect(url_for("manager.edit_playbook", company_id=company_id))

        script_store.write_playbook(
            company_id=company_id,
            markdown_text=markdown,
            source_type=source_type,
            source_ref=source_ref,
            manager_email=m["email"],
        )
        flash("Playbook updated.", "success")
        return redirect(url_for("manager.edit_playbook", company_id=company_id))

    markdown = script_store.read_playbook(company_id) or ""
    meta = script_store.read_playbook_meta(company_id)
    return render_template(
        "manager/edit_playbook.html",
        company_id=company_id,
        markdown=markdown,
        meta=meta,
    )


# ---------- publish toggle ----------

@manager_bp.route("/company/<company_id>/publish", methods=["POST"])
@auth.require_manager
def publish_toggle(company_id):
    m = auth.current_manager()
    if not script_store.is_company_in_agency(company_id, m["agency_slug"]):
        abort(404)
    script = script_store.get_script(company_id)
    script["published"] = not bool(script.get("published"))
    script_store.write_script(script)
    flash(f"{'Published' if script['published'] else 'Unpublished'}.", "success")
    return redirect(url_for("manager.dashboard"))
