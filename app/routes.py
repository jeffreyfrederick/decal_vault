import os
import uuid
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from .auth import check_password, is_staff, staff_required
from .models import CATEGORIES, LANGUAGES, STATUS_ACTIVE, STATUS_DISCONTINUED, STATUSES, Decal, EquipmentModel, db

bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Browse / search
# ---------------------------------------------------------------------------

SORT_OPTIONS = {
    "part_number": Decal.part_number.asc(),
    "model": EquipmentModel.name.asc(),
    "category": EquipmentModel.category.asc(),
    "status": Decal.status.asc(),
    "newest": Decal.created_at.desc(),
}


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    model_id = request.args.get("model_id", type=int)
    language = request.args.get("language", "").strip()
    status = request.args.get("status", STATUS_ACTIVE)
    sort = request.args.get("sort", "part_number")
    view = request.args.get("view", "cards")
    if view not in ("table", "cards"):
        view = "cards"

    query = Decal.query.outerjoin(Decal.models)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Decal.part_number.ilike(like), Decal.description.ilike(like)))
    if model_id:
        query = query.filter(EquipmentModel.id == model_id)
    if category:
        query = query.filter(EquipmentModel.category == category)
    if language:
        query = query.filter(Decal.language == language)
    if status in STATUSES:
        query = query.filter(Decal.status == status)
    # status == "all" (or anything unrecognized) leaves both statuses in view

    query = query.order_by(SORT_OPTIONS.get(sort, SORT_OPTIONS["part_number"]))
    decals = query.distinct().all()

    all_categories = [c for (c,) in db.session.query(EquipmentModel.category).distinct().order_by(EquipmentModel.category)]
    models = EquipmentModel.query.order_by(EquipmentModel.category, EquipmentModel.name).all()
    languages = [l for (l,) in db.session.query(Decal.language).distinct().order_by(Decal.language)]

    return render_template(
        "index.html",
        decals=decals,
        all_categories=all_categories,
        models=models,
        languages=languages,
        filters={
            "q": q,
            "category": category,
            "model_id": model_id,
            "language": language,
            "status": status,
            "sort": sort,
            "view": view,
        },
    )


# ---------------------------------------------------------------------------
# Auth (single shared staff password, this could be changed later)
# ---------------------------------------------------------------------------


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if check_password(request.form.get("password", "")):
            session["staff_authenticated"] = True
            next_url = request.args.get("next") or url_for("main.index")
            return redirect(next_url)
        flash("Incorrect password.", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.pop("staff_authenticated", None)
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Upload / create
# ---------------------------------------------------------------------------


def _allowed_image(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def _delete_image_file(image_filename):
    if not image_filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], image_filename)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _parse_model_ids(form):
    """Reads the repeatable model-picker rows from upload.html. Models come
    from the existing set only - creating or renaming one happens on the
    Manage page.
    """
    models = []
    seen = set()
    for raw_id in form.getlist("model_id"):
        if not raw_id or raw_id in seen:
            continue
        seen.add(raw_id)
        model = EquipmentModel.query.get(int(raw_id)) if raw_id.isdigit() else None
        if model:
            models.append(model)
    return models


@bp.route("/upload", methods=["GET", "POST"])
@staff_required
def upload():
    if request.method == "POST":
        part_number = request.form.get("part_number", "").strip()
        if not part_number:
            flash("Part number is required.", "danger")
            return render_template("upload.html", **_upload_context())

        models = _parse_model_ids(request.form)
        if not models:
            flash("At least one model is required.", "danger")
            return render_template("upload.html", **_upload_context())

        superseded_by_id, superseded_by_error = _resolve_superseded_by(request.form.get("superseded_by"))
        if superseded_by_error:
            flash(superseded_by_error, "danger")
            return render_template("upload.html", **_upload_context())

        decal = Decal(
            part_number=part_number,
            description=request.form.get("description", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            language=request.form.get("language", "EN").strip() or "EN",
            status=request.form.get("status") if request.form.get("status") in STATUSES else STATUS_ACTIVE,
            subcategory=request.form.get("subcategory", "").strip() or None,
            models=models,
            superseded_by_id=superseded_by_id,
        )

        image = request.files.get("image")
        if image and image.filename:
            if not _allowed_image(image.filename):
                flash("Unsupported image type.", "danger")
                return render_template("upload.html", **_upload_context())
            safe_name = secure_filename(image.filename)
            ext = safe_name.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            image.save(f"{current_app.config['UPLOAD_FOLDER']}/{filename}")
            decal.image_filename = filename
            decal.original_filename = safe_name

        db.session.add(decal)
        db.session.commit()
        flash(f"Decal {decal.part_number} added.", "success")
        return redirect(url_for("main.index"))

    return render_template("upload.html", **_upload_context())


@bp.route("/decal/<int:decal_id>/edit", methods=["GET", "POST"])
@staff_required
def edit_decal(decal_id):
    decal = Decal.query.get_or_404(decal_id)

    if request.method == "POST":
        part_number = request.form.get("part_number", "").strip()
        if not part_number:
            flash("Part number is required.", "danger")
            return render_template("upload.html", **_upload_context(decal))

        models = _parse_model_ids(request.form)
        if not models:
            flash("At least one model is required.", "danger")
            return render_template("upload.html", **_upload_context(decal))

        superseded_by_id, superseded_by_error = _resolve_superseded_by(request.form.get("superseded_by"), exclude_id=decal.id)
        if superseded_by_error:
            flash(superseded_by_error, "danger")
            return render_template("upload.html", **_upload_context(decal))

        decal.part_number = part_number
        decal.description = request.form.get("description", "").strip() or None
        decal.notes = request.form.get("notes", "").strip() or None
        decal.language = request.form.get("language", "EN").strip() or "EN"
        decal.status = request.form.get("status") if request.form.get("status") in STATUSES else decal.status
        decal.subcategory = request.form.get("subcategory", "").strip() or None
        decal.models = models
        decal.superseded_by_id = superseded_by_id

        image = request.files.get("image")
        if image and image.filename:
            if not _allowed_image(image.filename):
                flash("Unsupported image type.", "danger")
                return render_template("upload.html", **_upload_context(decal))
            safe_name = secure_filename(image.filename)
            ext = safe_name.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            image.save(f"{current_app.config['UPLOAD_FOLDER']}/{filename}")
            _delete_image_file(decal.image_filename)
            decal.image_filename = filename
            decal.original_filename = safe_name

        db.session.commit()
        flash(f"Decal {decal.part_number} updated.", "success")
        return redirect(url_for("main.index"))

    return render_template("upload.html", **_upload_context(decal))


def _resolve_superseded_by(raw, exclude_id=None):
    """Looks up a typed part number instead of offering a dropdown.
    Returns (decal_id, error_message) - error_message is set when the
    save should be blocked.
    """
    raw = (raw or "").strip()
    if not raw:
        return None, None
    candidate = Decal.query.filter_by(part_number=raw).first()
    if not candidate:
        return None, f'No decal found with part number "{raw}" for Superseded By.'
    if candidate.id == exclude_id:
        return None, "A decal can't supersede itself."
    return candidate.id, None


def _upload_context(decal=None):
    all_models = EquipmentModel.query.order_by(EquipmentModel.category, EquipmentModel.name).all()
    return {
        "decal": decal,
        "models": all_models,
        "categories": CATEGORIES,
        "statuses": STATUSES,
        "languages": LANGUAGES,
    }


# ---------------------------------------------------------------------------
# Status toggle / delete
# ---------------------------------------------------------------------------


@bp.route("/decal/<int:decal_id>/toggle-status", methods=["POST"])
@staff_required
def toggle_status(decal_id):
    decal = Decal.query.get_or_404(decal_id)
    decal.status = STATUS_DISCONTINUED if decal.status == STATUS_ACTIVE else STATUS_ACTIVE
    db.session.commit()
    flash(f"Decal {decal.part_number} marked {decal.status}.", "success")
    return redirect(request.referrer or url_for("main.index"))


@bp.route("/decal/<int:decal_id>/delete", methods=["POST"])
@staff_required
def delete_decal(decal_id):
    # Hard delete, for fixing bad data entry. Discontinued decals stay in
    # the DB and get flagged instead - this route is only for mistakes.
    decal = Decal.query.get_or_404(decal_id)
    part_number = decal.part_number
    _delete_image_file(decal.image_filename)
    db.session.delete(decal)
    db.session.commit()
    flash(f"Decal {part_number} deleted.", "success")
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Manage models / categories
# ---------------------------------------------------------------------------


@bp.route("/manage")
@staff_required
def manage():
    all_models = EquipmentModel.query.order_by(EquipmentModel.category, EquipmentModel.name).all()
    models_by_category = {}
    for category in CATEGORIES:
        models_by_category[category] = [m for m in all_models if m.category == category]
    return render_template("manage.html", models_by_category=models_by_category, categories=CATEGORIES)


@bp.route("/manage/model/add", methods=["POST"])
@staff_required
def add_model():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    if not name:
        flash("Model name can't be blank.", "danger")
        return redirect(url_for("main.manage"))
    if category not in CATEGORIES:
        flash(f'"{category}" isn\'t a recognized category.', "danger")
        return redirect(url_for("main.manage"))

    existing = EquipmentModel.query.filter(
        db.func.lower(EquipmentModel.name) == name.lower(),
        db.func.lower(EquipmentModel.category) == category.lower(),
    ).first()
    if existing:
        flash(f'"{name}" already exists under {category}.', "danger")
        return redirect(url_for("main.manage"))

    db.session.add(EquipmentModel(name=name, category=category))
    db.session.commit()
    flash(f'Model "{name}" added under {category}.', "success")
    return redirect(url_for("main.manage"))


@bp.route("/manage/model/<int:model_id>/rename", methods=["POST"])
@staff_required
def rename_model(model_id):
    model = EquipmentModel.query.get_or_404(model_id)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Model name can't be blank.", "danger")
        return redirect(url_for("main.manage"))

    model.name = name
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'A model named "{name}" already exists in "{model.category}".', "danger")
        return redirect(url_for("main.manage"))

    flash(f'Model renamed to "{name}".', "success")
    return redirect(url_for("main.manage"))


@bp.route("/manage/model/<int:model_id>/delete", methods=["POST"])
@staff_required
def delete_model(model_id):
    model = EquipmentModel.query.get_or_404(model_id)
    if model.decals:
        flash(f'"{model.name}" is still used by {len(model.decals)} decal(s) - remove it from those first.', "danger")
        return redirect(url_for("main.manage"))

    db.session.delete(model)
    db.session.commit()
    flash(f'Model "{model.name}" deleted.', "success")
    return redirect(url_for("main.manage"))
