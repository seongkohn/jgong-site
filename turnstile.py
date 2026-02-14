import json
import urllib.request
import urllib.parse
from flask import request, current_app


def verify_turnstile():
    """Verify Cloudflare Turnstile token from form submission. Returns True if valid."""
    token = request.form.get("cf-turnstile-response", "")
    secret = current_app.config["TURNSTILE_SECRET_KEY"]

    if not token or not secret:
        return False

    data = urllib.parse.urlencode({
        "secret": secret,
        "response": token,
        "remoteip": request.remote_addr,
    }).encode()

    try:
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=data,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            return result.get("success", False)
    except Exception:
        return False
