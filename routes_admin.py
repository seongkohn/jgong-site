import os
import uuid
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
from db import get_db, get_setting, set_setting
from models import Admin

admin_bp = Blueprint("admin_bp", __name__)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_DIMENSION = 1920  # px – longest side


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _save_image(file):
    if file and file.filename and _allowed(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        name = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], name)
        img = Image.open(file)
        img.exif_transpose(inplace=True) if hasattr(img, "exif_transpose") else None
        if max(img.size) > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        save_kwargs = {}
        if ext in ("jpg", "jpeg"):
            save_kwargs = {"quality": 85, "optimize": True}
        elif ext == "webp":
            save_kwargs = {"quality": 85}
        elif ext == "png":
            save_kwargs = {"optimize": True}
        img.save(path, **save_kwargs)
        return name
    return None


def _delete_image(filename):
    if filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(path):
            os.remove(path)


# ── Auth ────────────────────────────────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_bp.dashboard"))
    if request.method == "POST":
        user = Admin.get_by_username(request.form.get("username", ""))
        if user and user.check_password(request.form.get("password", "")):
            remember = bool(request.form.get("remember"))
            login_user(user, remember=remember)
            return redirect(url_for("admin_bp.dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("public_bp.index"))


# ── Dashboard ───────────────────────────────────────────────────────────

@admin_bp.route("/")
@login_required
def dashboard():
    db = get_db()
    works = db.execute("SELECT * FROM work ORDER BY sort_order, year DESC").fetchall()
    events = db.execute("SELECT * FROM event ORDER BY sort_order, date DESC").fetchall()
    gallery = db.execute("SELECT * FROM gallery ORDER BY sort_order").fetchall()
    messages = db.execute("SELECT * FROM message ORDER BY created_at DESC").fetchall()
    unread = db.execute("SELECT COUNT(*) FROM message WHERE is_read = 0").fetchone()[0]
    settings = {
        "recipient_email": get_setting("recipient_email"),
        "mail_server": get_setting("mail_server"),
        "mail_port": get_setting("mail_port"),
        "mail_username": get_setting("mail_username"),
        "mail_password": get_setting("mail_password"),
    }
    return render_template(
        "admin/dashboard.html",
        works=works, events=events, gallery=gallery,
        messages=messages, unread=unread, settings=settings,
    )


# ── Gallery CRUD ────────────────────────────────────────────────────────

@admin_bp.route("/gallery/add", methods=["POST"])
@login_required
def gallery_add():
    img = _save_image(request.files.get("image"))
    if not img:
        flash("Please select a valid image.", "error")
        return redirect(url_for("admin_bp.dashboard"))
    db = get_db()
    max_order = db.execute("SELECT COALESCE(MAX(sort_order),0) FROM gallery").fetchone()[0]
    db.execute(
        "INSERT INTO gallery (image_filename, caption, sort_order) VALUES (?, ?, ?)",
        (img, request.form.get("caption") or None, max_order + 1),
    )
    db.commit()
    flash("Photo added to gallery.", "success")
    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/gallery/<int:photo_id>/delete", methods=["POST"])
@login_required
def gallery_delete(photo_id):
    db = get_db()
    photo = db.execute("SELECT * FROM gallery WHERE id = ?", (photo_id,)).fetchone()
    if photo:
        _delete_image(photo["image_filename"])
        db.execute("DELETE FROM gallery WHERE id = ?", (photo_id,))
        db.commit()
        flash("Photo removed.", "success")
    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/gallery/<int:photo_id>/move/<direction>", methods=["POST"])
@login_required
def gallery_move(photo_id, direction):
    if direction in ("up", "down"):
        _swap("gallery", photo_id, direction)
    return redirect(url_for("admin_bp.dashboard"))


# ── Works CRUD ──────────────────────────────────────────────────────────

@admin_bp.route("/works/new", methods=["GET", "POST"])
@login_required
def work_new():
    if request.method == "POST":
        img = _save_image(request.files.get("image"))
        db = get_db()
        max_order = db.execute("SELECT COALESCE(MAX(sort_order),0) FROM work").fetchone()[0]
        db.execute(
            "INSERT INTO work (title, year, duration, description, performers, image_filename, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                request.form["title"],
                request.form.get("year") or None,
                request.form.get("duration") or None,
                request.form.get("description") or None,
                request.form.get("performers") or None,
                img,
                max_order + 1,
            ),
        )
        work_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        video_urls = request.form.getlist("video_urls[]")
        for i, url in enumerate(video_urls):
            url = url.strip()
            if url:
                db.execute(
                    "INSERT INTO work_video (work_id, video_url, sort_order) VALUES (?, ?, ?)",
                    (work_id, url, i),
                )
        db.commit()
        flash("Work added.", "success")
        return redirect(url_for("admin_bp.dashboard"))
    return render_template("admin/work_form.html", work=None, videos=[])


@admin_bp.route("/works/<int:work_id>/edit", methods=["GET", "POST"])
@login_required
def work_edit(work_id):
    db = get_db()
    work = db.execute("SELECT * FROM work WHERE id = ?", (work_id,)).fetchone()
    if not work:
        flash("Work not found.", "error")
        return redirect(url_for("admin_bp.dashboard"))

    if request.method == "POST":
        img = work["image_filename"]
        new_img = _save_image(request.files.get("image"))
        if new_img:
            _delete_image(img)
            img = new_img
        if request.form.get("remove_image"):
            _delete_image(img)
            img = None

        db.execute(
            "UPDATE work SET title=?, year=?, duration=?, description=?, performers=?, image_filename=? "
            "WHERE id=?",
            (
                request.form["title"],
                request.form.get("year") or None,
                request.form.get("duration") or None,
                request.form.get("description") or None,
                request.form.get("performers") or None,
                img,
                work_id,
            ),
        )
        db.execute("DELETE FROM work_video WHERE work_id = ?", (work_id,))
        video_urls = request.form.getlist("video_urls[]")
        for i, url in enumerate(video_urls):
            url = url.strip()
            if url:
                db.execute(
                    "INSERT INTO work_video (work_id, video_url, sort_order) VALUES (?, ?, ?)",
                    (work_id, url, i),
                )
        db.commit()
        flash("Work updated.", "success")
        return redirect(url_for("admin_bp.dashboard"))
    videos = db.execute(
        "SELECT * FROM work_video WHERE work_id = ? ORDER BY sort_order", (work_id,)
    ).fetchall()
    return render_template("admin/work_form.html", work=work, videos=videos)


@admin_bp.route("/works/<int:work_id>/delete", methods=["POST"])
@login_required
def work_delete(work_id):
    db = get_db()
    work = db.execute("SELECT * FROM work WHERE id = ?", (work_id,)).fetchone()
    if work:
        _delete_image(work["image_filename"])
        db.execute("DELETE FROM work WHERE id = ?", (work_id,))
        db.commit()
        flash("Work deleted.", "success")
    return redirect(url_for("admin_bp.dashboard"))


# ── Events CRUD ─────────────────────────────────────────────────────────

@admin_bp.route("/events/new", methods=["GET", "POST"])
@login_required
def event_new():
    if request.method == "POST":
        db = get_db()
        max_order = db.execute("SELECT COALESCE(MAX(sort_order),0) FROM event").fetchone()[0]
        db.execute(
            "INSERT INTO event (title, date, time, location, description, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form["title"],
                request.form.get("date") or None,
                request.form.get("time") or None,
                request.form.get("location") or None,
                request.form.get("description") or None,
                max_order + 1,
            ),
        )
        db.commit()
        flash("Event added.", "success")
        return redirect(url_for("admin_bp.dashboard"))
    return render_template("admin/event_form.html", event=None)


@admin_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def event_edit(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin_bp.dashboard"))

    if request.method == "POST":
        db.execute(
            "UPDATE event SET title=?, date=?, time=?, location=?, description=? WHERE id=?",
            (
                request.form["title"],
                request.form.get("date") or None,
                request.form.get("time") or None,
                request.form.get("location") or None,
                request.form.get("description") or None,
                event_id,
            ),
        )
        db.commit()
        flash("Event updated.", "success")
        return redirect(url_for("admin_bp.dashboard"))
    return render_template("admin/event_form.html", event=event)


@admin_bp.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def event_delete(event_id):
    db = get_db()
    db.execute("DELETE FROM event WHERE id = ?", (event_id,))
    db.commit()
    flash("Event deleted.", "success")
    return redirect(url_for("admin_bp.dashboard"))


# ── Reorder ─────────────────────────────────────────────────────────

def _swap(table, item_id, direction):
    """Swap sort_order of an item with its neighbour."""
    db = get_db()
    item = db.execute(f"SELECT id, sort_order FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return
    op = "<" if direction == "up" else ">"
    order = "DESC" if direction == "up" else "ASC"
    neighbour = db.execute(
        f"SELECT id, sort_order FROM {table} WHERE sort_order {op} ? ORDER BY sort_order {order} LIMIT 1",
        (item["sort_order"],),
    ).fetchone()
    if not neighbour:
        return
    db.execute(f"UPDATE {table} SET sort_order = ? WHERE id = ?", (neighbour["sort_order"], item["id"]))
    db.execute(f"UPDATE {table} SET sort_order = ? WHERE id = ?", (item["sort_order"], neighbour["id"]))
    db.commit()


@admin_bp.route("/works/<int:work_id>/move/<direction>", methods=["POST"])
@login_required
def work_move(work_id, direction):
    if direction in ("up", "down"):
        _swap("work", work_id, direction)
    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/events/<int:event_id>/move/<direction>", methods=["POST"])
@login_required
def event_move(event_id, direction):
    if direction in ("up", "down"):
        _swap("event", event_id, direction)
    return redirect(url_for("admin_bp.dashboard"))


# ── Messages ────────────────────────────────────────────────────────

@admin_bp.route("/messages/<int:msg_id>")
@login_required
def message_view(msg_id):
    db = get_db()
    msg = db.execute("SELECT * FROM message WHERE id = ?", (msg_id,)).fetchone()
    if not msg:
        flash("Message not found.", "error")
        return redirect(url_for("admin_bp.dashboard"))
    if not msg["is_read"]:
        db.execute("UPDATE message SET is_read = 1 WHERE id = ?", (msg_id,))
        db.commit()
    return render_template("admin/message_view.html", msg=msg)


@admin_bp.route("/messages/<int:msg_id>/delete", methods=["POST"])
@login_required
def message_delete(msg_id):
    db = get_db()
    db.execute("DELETE FROM message WHERE id = ?", (msg_id,))
    db.commit()
    flash("Message deleted.", "success")
    return redirect(url_for("admin_bp.dashboard"))


# ── Settings ────────────────────────────────────────────────────────

@admin_bp.route("/settings", methods=["POST"])
@login_required
def settings_update():
    for key in ("recipient_email", "mail_server", "mail_port", "mail_username", "mail_password"):
        val = request.form.get(key, "").strip()
        set_setting(key, val)
    flash("Settings updated.", "success")
    return redirect(url_for("admin_bp.dashboard"))
