import smtplib
from email.message import EmailMessage
from flask import Blueprint, render_template, request, flash, redirect, url_for
from db import get_db, get_setting
from turnstile import verify_turnstile

public_bp = Blueprint("public_bp", __name__)


@public_bp.route("/")
def index():
    db = get_db()
    events = db.execute(
        "SELECT * FROM event ORDER BY sort_order, date DESC LIMIT 3"
    ).fetchall()
    gallery = db.execute(
        "SELECT * FROM gallery ORDER BY sort_order"
    ).fetchall()
    return render_template("public/index.html", events=events, gallery=gallery)


@public_bp.route("/bio")
def bio():
    return render_template("public/bio.html")


@public_bp.route("/works")
def works():
    db = get_db()
    rows = db.execute("SELECT * FROM work ORDER BY sort_order, year DESC").fetchall()
    works = []
    for row in rows:
        w = dict(row)
        w["videos"] = db.execute(
            "SELECT title, video_url FROM work_video WHERE work_id = ? ORDER BY sort_order",
            (row["id"],),
        ).fetchall()
        works.append(w)
    return render_template("public/works.html", works=works)


@public_bp.route("/events")
def events():
    rows = get_db().execute("SELECT * FROM event ORDER BY sort_order, date DESC").fetchall()
    return render_template("public/events.html", events=rows)


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        if not verify_turnstile():
            flash("Verification failed. Please try again.", "error")
            return redirect(url_for("public_bp.contact"))

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        body = request.form.get("message", "").strip()

        if not name or not email or not body:
            flash("All fields are required.", "error")
            return redirect(url_for("public_bp.contact"))

        # Save to database
        db = get_db()
        db.execute(
            "INSERT INTO message (name, email, body) VALUES (?, ?, ?)",
            (name, email, body),
        )
        db.commit()

        # Send email
        mail_server = get_setting("mail_server")
        mail_port = int(get_setting("mail_port") or 587)
        mail_user = get_setting("mail_username")
        mail_pass = get_setting("mail_password")
        recipient = get_setting("recipient_email")
        if mail_user and mail_pass and recipient:
            try:
                msg = EmailMessage()
                msg["Subject"] = f"[Jingmian Gong] Message from {name}"
                msg["From"] = mail_user
                msg["To"] = recipient
                msg["Reply-To"] = email
                msg.set_content(
                    f"From: {name}\n"
                    f"Email: {email}\n"
                    f"{'─' * 40}\n\n"
                    f"{body}"
                )
                with smtplib.SMTP(mail_server, mail_port) as server:
                    server.starttls()
                    server.login(mail_user, mail_pass)
                    server.send_message(msg)
            except Exception:
                pass  # Message is saved in DB even if email fails

        flash("Message sent. Thank you!", "success")
        return redirect(url_for("public_bp.contact"))

    return render_template("public/contact.html")
