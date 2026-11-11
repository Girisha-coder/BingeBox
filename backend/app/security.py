import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from fastapi import HTTPException, Request, Response

COOKIE = "bingebox_session"


def hash_password(value):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(value, stored):
    try:
        algorithm, n, r, p, salt, digest = stored.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            value.encode(),
            salt=bytes.fromhex(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def sign(payload, lifetime=43200):
    secret = os.environ.get("AUTH_SECRET")
    if not secret:
        raise HTTPException(503, "Authentication is not configured.")
    raw = (
        base64.urlsafe_b64encode(
            json.dumps(
                {**payload, "exp": int(time.time()) + lifetime}, separators=(",", ":")
            ).encode()
        )
        .decode()
        .rstrip("=")
    )
    mac = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + mac


def read(token):
    try:
        raw, mac = token.split(".")
        expected = hmac.new(
            os.environ["AUTH_SECRET"].encode(), raw.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(mac, expected):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if payload["exp"] <= time.time():
            raise ValueError()
        return payload
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, "Please sign in again.") from None


def identity(request: Request, optional=False):
    token = request.cookies.get(COOKIE)
    if not token:
        if optional:
            return None
        raise HTTPException(401, "Please sign in.")
    return read(token)


def cookie(response: Response, payload):
    response.set_cookie(
        COOKIE,
        sign(payload),
        httponly=True,
        samesite="lax",
        secure=os.environ.get("COOKIE_SECURE") == "true",
        max_age=43200,
        path="/",
    )


def account(request, manage=False):
    who = identity(request)
    if who.get("kind") != "account":
        raise HTTPException(403, "Use an account login.")
    if manage and who.get("kids"):
        raise HTTPException(
            403, "Enter the account password to leave the kids profile."
        )
    return who


def profile(request, connection):
    who = account(request)
    row = connection.execute(
        "SELECT * FROM profile WHERE profile_id=%s AND account_id=%s",
        (who.get("profile_id"), who["id"]),
    ).fetchone()
    if not row:
        raise HTTPException(403, "Choose a viewer profile first.")
    return who, row


def admin(request, connection, roles=("catalogue", "billing", "super")):
    who = identity(request)
    if who.get("kind") != "admin":
        raise HTTPException(403, "Staff login required.")
    row = connection.execute(
        "SELECT admin_id,email,role,full_name FROM admin_user WHERE admin_id=%s",
        (who["id"],),
    ).fetchone()
    if not row or (row["role"] != "super" and row["role"] not in roles):
        raise HTTPException(403, "Your staff role cannot perform this action.")
    return row
