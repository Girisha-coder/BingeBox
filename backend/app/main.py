from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal
import os
import json
import re
import subprocess
import threading
import shutil
import psycopg
from psycopg import sql
from fastapi import FastAPI, HTTPException, Request, Response, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from .database import connect
from . import security as sec
from .queries import UP_NEXT, TOP_GENRE, RECOMMEND, REPORTS

app = FastAPI(title="BingeBox", version="1.0.0")
MEDIA = Path(os.environ.get("MEDIA_ROOT", "media")).resolve()
media_lock = threading.Lock()


@app.middleware("http")
async def protect_origin(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        allowed = {
            os.environ.get("APP_ORIGIN", "http://localhost:18080"),
            "http://127.0.0.1:18080",
            "http://localhost:18000",
            "http://testserver",
        }
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Unrecognised request origin."}, 403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(psycopg.Error)
async def database_error(request, error):
    code = error.sqlstate
    if code == "23505":
        detail, status = (
            "This record already exists. Choose another name or update the existing record.",
            409,
        )
    elif code == "23503":
        detail, status = (
            "This record is missing or still referenced by another item.",
            409,
        )
    elif code == "42501":
        detail, status = "Your role cannot perform this action.", 403
    elif code == "23514":
        message = error.diag.message_primary or ""
        detail = (
            message
            if not message.startswith("new row")
            else "A value conflicts with the allowed limits."
        )
        status = 400
    elif code in ("23502", "22001", "22P02", "22003"):
        detail, status = "Check the required fields and allowed values.", 400
    else:
        detail, status = "Database is temporarily unavailable.", 503
    return JSONResponse({"detail": detail}, status)


class Plan(BaseModel):
    plan_id: int
    name: str
    monthly_price: Decimal
    max_profiles: int
    max_streams: int
    max_quality: Literal["SD", "HD", "4K"]


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    staff: bool = False


class ProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    is_kids: bool = False
    max_age_rating: Literal[0, 7, 13, 16, 18] = 18


class PlaybackInput(BaseModel):
    movie_id: int | None = None
    episode_id: int | None = None
    device: str = Field(min_length=8, max_length=50)
    device_type: Literal["web", "mobile", "tablet", "tv"] = "web"
    replay: bool = False


class ProgressInput(BaseModel):
    token: str
    position: int = Field(ge=0)


class ReviewInput(BaseModel):
    rating: int = Field(ge=1, le=10)
    review_text: str | None = Field(default=None, max_length=2000)


class SubscriptionInput(BaseModel):
    plan_id: int


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    with connect() as db:
        db.execute("SELECT plan_id FROM plan LIMIT 1").fetchone()
    return {"status": "ready", "database": "ok"}


@app.get("/plans", response_model=list[Plan])
def plans():
    with connect() as db:
        return db.execute(
            "SELECT * FROM plan ORDER BY monthly_price,plan_id"
        ).fetchall()


@app.post("/auth/signup", status_code=201)
def signup(body: Credentials, response: Response):
    if len(body.password) < 8:
        raise HTTPException(400, "Use at least eight characters for your password.")
    if body.staff:
        raise HTTPException(403, "Staff accounts are provisioned separately.")
    with connect() as db:
        row = db.execute(
            "INSERT INTO account(email,password_hash) VALUES(%s,%s) RETURNING account_id,email",
            (body.email.strip().lower(), sec.hash_password(body.password)),
        ).fetchone()
    sec.cookie(response, {"kind": "account", "id": row["account_id"]})
    return {"email": row["email"], "kind": "account"}


@app.post("/auth/login")
def login(body: Credentials, response: Response):
    table = "admin_user" if body.staff else "account"
    key = "admin_id" if body.staff else "account_id"
    with connect() as db:
        row = db.execute(
            sql.SQL("SELECT * FROM {} WHERE lower(email)=%s").format(
                sql.Identifier(table)
            ),
            (body.email.strip().lower(),),
        ).fetchone()
    if not row or not sec.verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    sec.cookie(response, {"kind": "admin" if body.staff else "account", "id": row[key]})
    return {"kind": "admin" if body.staff else "account", "email": row["email"]}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(sec.COOKIE, path="/")
    return {"ok": True}


@app.get("/me")
def me(request: Request):
    who = sec.identity(request, optional=True)
    if not who:
        return {"kind": "guest"}
    with connect() as db:
        if who["kind"] == "admin":
            return {"kind": "admin", **sec.admin(request, db)}
        a = db.execute(
            "SELECT account_id,email,suspended_at FROM account WHERE account_id=%s",
            (who["id"],),
        ).fetchone()
        if not a:
            raise HTTPException(401, "Account no longer exists.")
        pr = db.execute(
            "SELECT profile_id,name,is_kids,max_age_rating FROM profile WHERE profile_id=%s AND account_id=%s",
            (who.get("profile_id"), who["id"]),
        ).fetchone()
    return {"kind": "account", **a, "profile": pr, "kids_locked": bool(who.get("kids"))}


@app.get("/profiles")
def profiles(request: Request):
    who = sec.account(request, manage=True)
    with connect() as db:
        return db.execute(
            "SELECT * FROM profile WHERE account_id=%s ORDER BY profile_id",
            (who["id"],),
        ).fetchall()


@app.post("/profiles", status_code=201)
def create_profile(body: ProfileInput, request: Request):
    who = sec.account(request, manage=True)
    if not body.name.strip():
        raise HTTPException(400, "Enter a profile name.")
    with connect() as db:
        return db.execute(
            "INSERT INTO profile(account_id,name,is_kids,max_age_rating) VALUES(%s,%s,%s,%s) RETURNING *",
            (who["id"], body.name.strip(), body.is_kids, body.max_age_rating),
        ).fetchone()


@app.patch("/profiles/{profile_id}")
def update_profile(profile_id: int, body: ProfileInput, request: Request):
    who = sec.account(request, manage=True)
    if not body.name.strip():
        raise HTTPException(400, "Enter a profile name.")
    with connect() as db:
        db.execute("SELECT 1 FROM account WHERE account_id=%s FOR UPDATE", (who["id"],))
        if not db.execute(
            "SELECT 1 FROM profile WHERE profile_id=%s AND account_id=%s",
            (profile_id, who["id"]),
        ).fetchone():
            raise HTTPException(404, "Profile not found.")
        if db.execute(
            "SELECT 1 FROM watch_history WHERE profile_id=%s AND item_age_rating(movie_id,episode_id)>%s LIMIT 1",
            (profile_id, body.max_age_rating),
        ).fetchone():
            raise HTTPException(
                409,
                "Create a new kids profile; existing history exceeds that age limit.",
            )
        return db.execute(
            "UPDATE profile SET name=%s,is_kids=%s,max_age_rating=%s WHERE profile_id=%s RETURNING *",
            (body.name.strip(), body.is_kids, body.max_age_rating, profile_id),
        ).fetchone()


@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, request: Request):
    who = sec.account(request, manage=True)
    with connect() as db:
        db.execute("SELECT 1 FROM account WHERE account_id=%s FOR UPDATE", (who["id"],))
        row = db.execute(
            "DELETE FROM profile WHERE profile_id=%s AND account_id=%s RETURNING profile_id",
            (profile_id, who["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Profile not found.")
    return {"ok": True}


@app.post("/profiles/{profile_id}/select")
def select_profile(profile_id: int, request: Request, response: Response):
    who = sec.account(request, manage=True)
    with connect() as db:
        row = db.execute(
            "SELECT * FROM profile WHERE profile_id=%s AND account_id=%s",
            (profile_id, who["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Profile not found.")
    sec.cookie(
        response,
        {
            "kind": "account",
            "id": who["id"],
            "profile_id": profile_id,
            "kids": row["is_kids"],
        },
    )
    return row


@app.post("/account/unlock")
def unlock(body: dict, request: Request, response: Response):
    who = sec.account(request)
    with connect() as db:
        row = db.execute(
            "SELECT password_hash FROM account WHERE account_id=%s", (who["id"],)
        ).fetchone()
    if not row or not sec.verify_password(
        str(body.get("password", "")), row["password_hash"]
    ):
        raise HTTPException(401, "Account password is incorrect.")
    sec.cookie(response, {"kind": "account", "id": who["id"]})
    return {"ok": True}


@app.get("/account")
def account_status(request: Request):
    who = sec.account(request, manage=True)
    with connect() as db:
        status = db.execute(
            "SELECT * FROM v_account_status WHERE account_id=%s", (who["id"],)
        ).fetchone()
        status["subscriptions"] = db.execute(
            "SELECT s.*,p.name FROM subscription s JOIN plan p USING(plan_id) WHERE account_id=%s ORDER BY sub_id DESC",
            (who["id"],),
        ).fetchall()
        status["sessions"] = db.execute(
            "SELECT ss.*,p.name FROM stream_session ss JOIN profile p USING(profile_id) WHERE p.account_id=%s AND ended_at IS NULL ORDER BY session_id DESC",
            (who["id"],),
        ).fetchall()
    return status


@app.post("/account/subscribe")
def subscribe(body: SubscriptionInput, request: Request):
    who = sec.account(request, manage=True)
    with connect() as db:
        return db.execute(
            "SELECT subscribe(%s,%s) AS sub_id", (who["id"], body.plan_id)
        ).fetchone()


@app.post("/account/change-plan")
def change_plan(body: SubscriptionInput, request: Request):
    who = sec.account(request, manage=True)
    with connect() as db:
        return db.execute(
            "SELECT change_plan(%s,%s) AS sub_id", (who["id"], body.plan_id)
        ).fetchone()


@app.patch("/account/auto-renew")
def auto_renew(body: dict, request: Request):
    who = sec.account(request, manage=True)
    if type(body.get("enabled")) is not bool:
        raise HTTPException(400, "Choose whether auto-renew is enabled.")
    with connect() as db:
        db.execute("SELECT 1 FROM account WHERE account_id=%s FOR UPDATE", (who["id"],))
        db.execute(
            "UPDATE subscription SET auto_renew=%s WHERE account_id=%s AND status IN('active','past_due')",
            (body["enabled"], who["id"]),
        )
    return {"ok": True}


@app.delete("/account/sessions/{session_id}")
def stop_device(session_id: int, request: Request):
    who = sec.account(request, manage=True)
    with connect() as db:
        if not db.execute(
            "SELECT 1 FROM stream_session ss JOIN profile p USING(profile_id) WHERE session_id=%s AND account_id=%s",
            (session_id, who["id"]),
        ).fetchone():
            raise HTTPException(404, "Device not found.")
        db.execute("SELECT end_playback(%s)", (session_id,))
    return {"ok": True}


def viewer(request, db):
    who = sec.identity(request, optional=True)
    if who and who.get("kind") == "account" and who.get("profile_id"):
        _, pr = sec.profile(request, db)
        return pr
    return None


@app.get("/catalog")
def catalog(
    request: Request,
    q: str = Query("", max_length=150),
    genre: str = "",
    audio: str = "",
    subtitle: str = "",
    min_runtime: int = Query(0, ge=0),
    max_runtime: int = Query(100000, ge=0),
    min_rating: float = Query(0, ge=0, le=10),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=60),
):
    with connect() as db:
        pr = viewer(request, db)
        age = pr["max_age_rating"] if pr else 18
        conditions = """v.age_rating<=%(age)s AND (%(genre)s='' OR %(genre)s=ANY(v.genres))
        AND (%(audio)s='' OR %(audio)s=ANY(v.audio_languages)) AND (%(subtitle)s='' OR %(subtitle)s=ANY(v.subtitle_languages))
        AND v.runtime_min BETWEEN %(min)s AND %(max)s AND (%(rating)s=0 OR v.imdb_rating>=%(rating)s)
        AND (%(q)s='' OR to_tsvector('english',v.name||' '||coalesce(v.description,'')) @@ plainto_tsquery('english',%(q)s)
             OR v.name ILIKE %(like)s OR similarity(v.name,%(q)s)>0.15)"""
        params = {
            "age": age,
            "genre": genre,
            "audio": audio,
            "subtitle": subtitle,
            "min": min_runtime,
            "max": max_runtime,
            "rating": min_rating,
            "q": q.strip(),
            "like": "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",
            "limit": limit,
            "offset": (page - 1) * limit,
        }
        projection = "v.*" if pr else "g.*"
        rows = db.execute(
            f"SELECT {projection} FROM v_title_catalog v JOIN v_guest_catalog g USING(title_id) WHERE {conditions} ORDER BY CASE WHEN %(q)s='' THEN 0 ELSE similarity(v.name,%(q)s) END DESC,v.title_id LIMIT %(limit)s OFFSET %(offset)s",
            params,
        ).fetchall()
        count = db.execute(
            f"SELECT count(*) AS total FROM v_title_catalog v WHERE {conditions}",
            params,
        ).fetchone()["total"]
    return {
        "items": rows,
        "total": count,
        "page": page,
        "limit": limit,
        "preview": not bool(pr),
    }


@app.get("/catalog/filters")
def filters():
    with connect() as db:
        return {
            "genres": [
                r["name"] for r in db.execute("SELECT name FROM genre ORDER BY name")
            ],
            "audio": [
                r["language"]
                for r in db.execute(
                    "SELECT DISTINCT language FROM title_audio ORDER BY language"
                )
            ],
            "subtitle": [
                r["language"]
                for r in db.execute(
                    "SELECT DISTINCT language FROM title_subtitle ORDER BY language"
                )
            ],
        }


@app.get("/catalog/{title_id}")
def title_detail(title_id: int, request: Request):
    with connect() as db:
        pr = viewer(request, db)
        if pr:
            row = db.execute(
                "SELECT * FROM v_title_catalog WHERE title_id=%s AND age_rating<=%s",
                (title_id, pr["max_age_rating"]),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Title unavailable for this profile.")
            row["episodes"] = db.execute(
                "SELECT e.*,r.rating AS my_rating FROM episode e LEFT JOIN episode_rating r ON r.episode_id=e.episode_id AND r.profile_id=%s WHERE e.series_id=%s ORDER BY season_no,episode_no",
                (pr["profile_id"], title_id),
            ).fetchall()
            row["reviews"] = db.execute(
                "SELECT r.*,p.name FROM title_review r JOIN profile p USING(profile_id) WHERE title_id=%s ORDER BY updated_at DESC,profile_id",
                (title_id,),
            ).fetchall()
        else:
            row = db.execute(
                "SELECT * FROM v_guest_catalog WHERE title_id=%s", (title_id,)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Title not found.")
    return {**row, "preview": not bool(pr)}


@app.get("/home")
def home(request: Request):
    with connect() as db:
        _, pr = sec.profile(request, db)
        pid = pr["profile_id"]
        age = pr["max_age_rating"]
        return {
            "continue_watching": db.execute(
                "SELECT * FROM v_continue_watching WHERE profile_id=%s ORDER BY last_watched_at DESC,watch_id DESC LIMIT 12",
                (pid,),
            ).fetchall(),
            "up_next": db.execute(UP_NEXT, (pid, age)).fetchall(),
            "recommendations": db.execute(RECOMMEND, (pid, age)).fetchall(),
            "top_genres": db.execute(TOP_GENRE, (age,)).fetchall(),
        }


@app.put("/catalog/{title_id}/review")
def review(title_id: int, body: ReviewInput, request: Request):
    with connect() as db:
        _, pr = sec.profile(request, db)
        return db.execute(
            "INSERT INTO title_review(profile_id,title_id,rating,review_text) VALUES(%s,%s,%s,%s) ON CONFLICT(profile_id,title_id) DO UPDATE SET rating=excluded.rating,review_text=excluded.review_text,updated_at=CURRENT_DATE RETURNING *",
            (pr["profile_id"], title_id, body.rating, body.review_text),
        ).fetchone()


@app.delete("/catalog/{title_id}/review")
def delete_review(title_id: int, request: Request):
    with connect() as db:
        _, pr = sec.profile(request, db)
        db.execute(
            "DELETE FROM title_review WHERE title_id=%s AND profile_id=%s",
            (title_id, pr["profile_id"]),
        )
    return {"ok": True}


@app.put("/episodes/{episode_id}/rating")
def episode_rating(episode_id: int, body: ReviewInput, request: Request):
    with connect() as db:
        _, pr = sec.profile(request, db)
        return db.execute(
            "INSERT INTO episode_rating(profile_id,episode_id,rating) VALUES(%s,%s,%s) ON CONFLICT(profile_id,episode_id) DO UPDATE SET rating=excluded.rating,rated_at=CURRENT_DATE RETURNING *",
            (pr["profile_id"], episode_id, body.rating),
        ).fetchone()


@app.delete("/episodes/{episode_id}/rating")
def delete_rating(episode_id: int, request: Request):
    with connect() as db:
        _, pr = sec.profile(request, db)
        db.execute(
            "DELETE FROM episode_rating WHERE episode_id=%s AND profile_id=%s",
            (episode_id, pr["profile_id"]),
        )
    return {"ok": True}


def placeholder(runtime):
    target = MEDIA / "placeholder" / f"{runtime}.mp4"
    if target.exists():
        return target
    with media_lock:
        if target.exists():
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp.mp4")
        try:
            font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            if os.name == "nt":
                shutil.copyfile(
                    Path(os.environ.get("WINDIR", "C:/Windows"))
                    / "Fonts"
                    / "arial.ttf",
                    target.parent / "font.ttf",
                )
                font = "font.ttf"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=0x17252c:s=640x360:r=1/5",
                    "-vf",
                    f"drawbox=x=0:y=290:w=640:h=70:color=0xc94c43:t=fill,drawtext=fontfile={font}:text='BINGEBOX - DEMO PLACEHOLDER':fontcolor=white:fontsize=24:x=(w-tw)/2:y=(h-th)/2",
                    "-t",
                    str(runtime),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "32",
                    "-pix_fmt",
                    "yuv420p",
                    "-g",
                    "1",
                    "-movflags",
                    "+faststart",
                    "-an",
                    str(temporary),
                ],
                check=True,
                timeout=180,
                cwd=target.parent,
            )
            temporary.replace(target)
        except (OSError, subprocess.SubprocessError):
            temporary.unlink(missing_ok=True)
            raise HTTPException(
                503, "The placeholder video could not be prepared. Please try again."
            ) from None
    return target


@app.post("/playback/start")
def start_playback(body: PlaybackInput, request: Request):
    with connect() as db:
        who, pr = sec.profile(request, db)
        result = db.execute(
            "SELECT start_playback(%s,%s,%s,%s,%s,%s) AS result",
            (
                pr["profile_id"],
                body.movie_id,
                body.episode_id,
                body.device,
                body.replay,
                body.device_type,
            ),
        ).fetchone()["result"]
    try:
        if result["is_placeholder"]:
            placeholder(result["runtime_sec"])
    except HTTPException:
        with connect() as db:
            db.execute("SELECT end_playback(%s)", (result["session_id"],))
        raise
    token = sec.sign(
        {
            **result,
            "kind": "playback",
            "account_id": who["id"],
            "profile_id": pr["profile_id"],
        },
        lifetime=86400,
    )
    return {**result, "token": token, "media_url": "/api/media/" + token}


def playback_identity(token, request, db, live=True):
    play = sec.read(token)
    who, pr = sec.profile(request, db)
    if (
        play.get("kind") != "playback"
        or play.get("account_id") != who["id"]
        or play.get("profile_id") != pr["profile_id"]
    ):
        raise HTTPException(403, "Playback belongs to another profile.")
    row = db.execute(
        "SELECT * FROM stream_session WHERE session_id=%s AND profile_id=%s",
        (play["session_id"], pr["profile_id"]),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Playback session not found.")
    if live:
        valid = db.execute(
            "SELECT (current_plan(%s)).plan_id AS plan_id,suspended_at FROM account WHERE account_id=%s",
            (who["id"], who["id"]),
        ).fetchone()
        age = db.execute(
            "SELECT item_age_rating(%s,%s) AS age",
            (play["movie_id"], play["episode_id"]),
        ).fetchone()["age"]
        if (
            row["ended_at"] is not None
            or not valid
            or not valid["plan_id"]
            or valid["suspended_at"]
            or age is None
            or age > pr["max_age_rating"]
        ):
            raise HTTPException(403, "Playback is no longer authorised.")
    return play


@app.post("/playback/progress")
def progress(body: ProgressInput, request: Request):
    with connect() as db:
        play = playback_identity(body.token, request, db)
        return db.execute(
            "SELECT * FROM record_progress(%s,%s,%s)",
            (play["session_id"], play["watch_id"], body.position),
        ).fetchone()


@app.post("/playback/stop")
def stop(body: dict, request: Request):
    with connect() as db:
        play = playback_identity(str(body.get("token", "")), request, db, live=False)
        db.execute(
            "SELECT 1 FROM account WHERE account_id=%s FOR UPDATE",
            (play["account_id"],),
        )
        pos = body.get("position")
        if pos is not None:
            if type(pos) is not int or not 0 <= pos <= play["runtime_sec"]:
                raise HTTPException(400, "Invalid playback position.")
            # A revoked session can still be closed; it cannot write more progress.
            valid = db.execute(
                "SELECT ss.ended_at IS NULL AND a.suspended_at IS NULL AND (current_plan(a.account_id)).plan_id IS NOT NULL AS live FROM stream_session ss JOIN profile p USING(profile_id) JOIN account a USING(account_id) WHERE session_id=%s",
                (play["session_id"],),
            ).fetchone()
            if valid["live"]:
                db.execute(
                    "SELECT end_playback(%s,%s,%s)",
                    (play["session_id"], play["watch_id"], pos),
                )
        db.execute("SELECT end_playback(%s)", (play["session_id"],))
    return {"ok": True}


@app.get("/media/{token}")
def media(token: str, request: Request):
    with connect() as db:
        play = playback_identity(token, request, db)
    if play["is_placeholder"]:
        path = placeholder(play["runtime_sec"])
    else:
        path = (MEDIA / str(play["source_ref"])).resolve()
        if not path.is_relative_to(MEDIA) or not path.is_file():
            raise HTTPException(404, "Video file not available.")
    return FileResponse(
        path, media_type="video/mp4", headers={"Cache-Control": "no-store"}
    )


@app.get("/admin/accounts")
def admin_accounts(request: Request):
    with connect() as db:
        sec.admin(request, db, ("billing",))
        return db.execute(
            "SELECT * FROM v_account_status ORDER BY account_id"
        ).fetchall()


@app.post("/admin/accounts/{account_id}/{action}")
def account_action(account_id: int, action: str, request: Request):
    if action not in ("suspend", "reinstate"):
        raise HTTPException(404, "Action not found.")
    with connect() as db:
        staff = sec.admin(request, db, ("billing",))
        function = "suspend_account" if action == "suspend" else "reinstate_account"
        db.execute(
            sql.SQL("SELECT {}(%s,%s)").format(sql.Identifier(function)),
            (staff["admin_id"], account_id),
        )
    return {"ok": True}


@app.post("/admin/renewals")
def renewals(body: dict, request: Request):
    try:
        on_date = date.fromisoformat(body.get("date", ""))
    except (ValueError, TypeError):
        raise HTTPException(400, "Choose a valid renewal date.")
    with connect() as db:
        staff = sec.admin(request, db, ("billing",))
        return db.execute(
            "SELECT process_renewals(%s,%s) AS result", (staff["admin_id"], on_date)
        ).fetchone()["result"]


@app.get("/admin/reports/{name}")
def report(name: str, request: Request):
    if name not in REPORTS:
        raise HTTPException(404, "Report not found.")
    with connect() as db:
        sec.admin(request, db, ("billing",))
        return db.execute(REPORTS[name]).fetchall()


TABLES = {
    "titles": (
        "title",
        "title_id",
        {
            "name",
            "release_year",
            "description",
            "age_rating",
            "original_language",
            "imdb_id",
            "imdb_rating",
            "imdb_votes",
            "title_type",
        },
    ),
    "episodes": (
        "episode",
        "episode_id",
        {
            "series_id",
            "season_no",
            "episode_no",
            "name",
            "duration_min",
            "imdb_rating",
            "air_date",
        },
    ),
    "genres": ("genre", "genre_id", {"name"}),
    "videos": (
        "media_asset",
        "asset_id",
        {
            "asset_kind",
            "title_id",
            "movie_id",
            "episode_id",
            "provider",
            "source_ref",
            "quality",
            "duration_sec",
            "is_placeholder",
        },
    ),
    "plans": (
        "plan",
        "plan_id",
        {"name", "monthly_price", "max_profiles", "max_streams", "max_quality"},
    ),
}


def staff_table(resource, request, db):
    if resource not in TABLES:
        raise HTTPException(404, "Management area not found.")
    sec.admin(request, db, ("super",) if resource == "plans" else ("catalogue",))
    return TABLES[resource]


@app.get("/admin/manage/{resource}")
def admin_list(resource: str, request: Request):
    with connect() as db:
        table, key, _ = staff_table(resource, request, db)
        if resource == "titles":
            return db.execute(
                "SELECT v.*,m.duration_min,s.series_status FROM v_title_catalog v LEFT JOIN movie m USING(title_id) LEFT JOIN series s USING(title_id) ORDER BY v.title_id"
            ).fetchall()
        return db.execute(
            sql.SQL("SELECT * FROM {} ORDER BY {}").format(
                sql.Identifier(table), sql.Identifier(key)
            )
        ).fetchall()


def catalog_write(resource, item_id, body, request):
    with connect() as db:
        table, key, fields = staff_table(resource, request, db)
        values = {k: v for k, v in body.items() if k in fields}
        if not values:
            raise HTTPException(400, "Provide the required fields.")
        integer_fields = {
            "release_year",
            "age_rating",
            "imdb_votes",
            "duration_min",
            "series_id",
            "season_no",
            "episode_no",
            "title_id",
            "movie_id",
            "episode_id",
            "duration_sec",
            "max_profiles",
            "max_streams",
        }
        for field in integer_fields:
            if (
                field in body
                and body[field] is not None
                and type(body[field]) is not int
            ):
                raise HTTPException(
                    400,
                    f"{field.replace('_', ' ').capitalize()} must be a whole number.",
                )
        old = None
        if item_id is not None:
            old = db.execute(
                sql.SQL("SELECT * FROM {} WHERE {}=%s FOR UPDATE").format(
                    sql.Identifier(table), sql.Identifier(key)
                ),
                (item_id,),
            ).fetchone()
            if not old:
                raise HTTPException(404, "Record not found.")
        if resource == "plans" and old:
            db.execute(
                "SELECT account_id FROM account ORDER BY account_id FOR UPDATE"
            ).fetchall()
            quality = values.get("max_quality", old["max_quality"])
            if quality not in ("SD", "HD", "4K"):
                raise HTTPException(400, "Choose SD, HD or 4K.")
            reduced = any(
                k in values and int(values[k]) < old[k]
                for k in ("max_profiles", "max_streams")
            ) or ["SD", "HD", "4K"].index(quality) < ["SD", "HD", "4K"].index(
                old["max_quality"]
            )
            if (
                reduced
                and db.execute(
                    "SELECT 1 FROM subscription WHERE plan_id=%s AND status IN('active','past_due') LIMIT 1",
                    (item_id,),
                ).fetchone()
            ):
                raise HTTPException(
                    409, "Move active subscribers before reducing plan limits."
                )
        if (
            resource == "titles"
            and old
            and values.get("title_type", old["title_type"]) != old["title_type"]
        ):
            raise HTTPException(
                409,
                "A title type cannot be changed; create the appropriate title instead.",
            )
        if resource == "videos":
            merged = {**(old or {}), **values}
            provider = values.get("provider", old["provider"] if old else None)
            kind = values.get("asset_kind", old["asset_kind"] if old else None)
            if kind == "trailer" and provider != "youtube":
                raise HTTPException(400, "Trailers use a YouTube video ID.")
            if provider == "youtube" and not re.fullmatch(
                r"[A-Za-z0-9_-]{11}",
                str(values.get("source_ref", old["source_ref"] if old else "")),
            ):
                raise HTTPException(400, "Enter the 11-character YouTube video ID.")
            if kind == "full" and provider != "file":
                raise HTTPException(400, "Full videos must use local files.")
            if merged.get("is_placeholder") and merged.get("quality", "HD") != "SD":
                raise HTTPException(
                    400, "Generated placeholders are available in SD only."
                )
            if kind == "full" and not merged.get("is_placeholder"):
                path = (MEDIA / str(merged.get("source_ref", ""))).resolve()
                if not path.is_relative_to(MEDIA) or not path.is_file():
                    raise HTTPException(
                        400,
                        "Place the permitted MP4 in the media directory and enter its relative path.",
                    )
                try:
                    probe = json.loads(
                        subprocess.check_output(
                            [
                                "ffprobe",
                                "-v",
                                "error",
                                "-show_entries",
                                "format=duration",
                                "-of",
                                "json",
                                str(path),
                            ],
                            timeout=15,
                        )
                    )
                    actual = float(probe["format"]["duration"])
                    if abs(actual - int(merged.get("duration_sec", 0))) > 1:
                        raise ValueError()
                except (OSError, subprocess.SubprocessError, ValueError, KeyError):
                    raise HTTPException(
                        400,
                        "The actual video duration must match the asset duration within one second.",
                    ) from None
        if old:
            statement = sql.SQL("UPDATE {} SET {} WHERE {}=%s RETURNING *").format(
                sql.Identifier(table),
                sql.SQL(",").join(
                    sql.SQL("{}=%s").format(sql.Identifier(k)) for k in values
                ),
                sql.Identifier(key),
            )
            row = db.execute(statement, [*values.values(), item_id]).fetchone()
        else:
            statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
                sql.Identifier(table),
                sql.SQL(",").join(map(sql.Identifier, values)),
                sql.SQL(",").join(sql.Placeholder() for _ in values),
            )
            row = db.execute(statement, list(values.values())).fetchone()
            item_id = row[key]
        if resource == "titles":
            if (old is None or "genres" in body) and not body.get("genres"):
                raise HTTPException(400, "Choose at least one genre for this title.")
            if row["title_type"] == "M":
                duration = body.get("duration_min")
                if duration is None and old is None:
                    raise HTTPException(400, "Movie runtime is required.")
                if duration is not None:
                    prior = db.execute(
                        "SELECT duration_min FROM movie WHERE title_id=%s", (item_id,)
                    ).fetchone()
                    if (
                        prior
                        and int(duration) != prior["duration_min"]
                        and db.execute(
                            "SELECT 1 FROM media_asset WHERE movie_id=%s UNION ALL SELECT 1 FROM watch_history WHERE movie_id=%s LIMIT 1",
                            (item_id, item_id),
                        ).fetchone()
                    ):
                        raise HTTPException(
                            409,
                            "Runtime cannot change while assets or history reference this item.",
                        )
                    db.execute(
                        "INSERT INTO movie(title_id,duration_min) VALUES(%s,%s) ON CONFLICT(title_id) DO UPDATE SET duration_min=excluded.duration_min",
                        (item_id, duration),
                    )
            else:
                db.execute(
                    "INSERT INTO series(title_id,series_status) VALUES(%s,%s) ON CONFLICT(title_id) DO UPDATE SET series_status=excluded.series_status",
                    (item_id, body.get("series_status", "ongoing")),
                )
            for field, join_table, column in [
                ("genres", "title_genre", "genre_id"),
                ("audio_languages", "title_audio", "language"),
                ("subtitle_languages", "title_subtitle", "language"),
            ]:
                if field in body:
                    if not isinstance(body[field], list) or not all(
                        isinstance(v, str) and 0 < len(v) <= 30 for v in body[field]
                    ):
                        raise HTTPException(
                            400, "Provide a list of short, nonempty names."
                        )
                    db.execute(
                        sql.SQL("DELETE FROM {} WHERE title_id=%s").format(
                            sql.Identifier(join_table)
                        ),
                        (item_id,),
                    )
                    for value in set(body[field]):
                        if field == "genres":
                            value = db.execute(
                                "INSERT INTO genre(name) VALUES(%s) ON CONFLICT(name) DO UPDATE SET name=excluded.name RETURNING genre_id",
                                (value,),
                            ).fetchone()["genre_id"]
                        db.execute(
                            sql.SQL("INSERT INTO {}(title_id,{}) VALUES(%s,%s)").format(
                                sql.Identifier(join_table), sql.Identifier(column)
                            ),
                            (item_id, value),
                        )
        if (
            resource == "episodes"
            and old
            and any(
                values.get(k, old[k]) != old[k] for k in ("duration_min", "series_id")
            )
        ):
            if db.execute(
                "SELECT 1 FROM media_asset WHERE episode_id=%s UNION ALL SELECT 1 FROM watch_history WHERE episode_id=%s LIMIT 1",
                (item_id, item_id),
            ).fetchone():
                raise HTTPException(
                    409,
                    "Runtime cannot change while assets or history reference this episode.",
                )
        return row


@app.post("/admin/manage/{resource}", status_code=201)
def admin_create(resource: str, body: dict, request: Request):
    return catalog_write(resource, None, body, request)


@app.patch("/admin/manage/{resource}/{item_id}")
def admin_update(resource: str, item_id: int, body: dict, request: Request):
    return catalog_write(resource, item_id, body, request)


@app.delete("/admin/manage/{resource}/{item_id}")
def admin_delete(resource: str, item_id: int, request: Request):
    with connect() as db:
        table, key, _ = staff_table(resource, request, db)
        if resource in ("titles", "episodes"):
            condition = (
                "w.episode_id=%s"
                if resource == "episodes"
                else "coalesce(w.movie_id,e.series_id)=%s"
            )
            if db.execute(
                "SELECT 1 FROM watch_history w LEFT JOIN episode e USING(episode_id) WHERE "
                + condition
                + " LIMIT 1",
                (item_id,),
            ).fetchone():
                raise HTTPException(
                    409, "This item has watch history and cannot be deleted."
                )
        if resource == "titles":
            db.execute("DELETE FROM movie WHERE title_id=%s", (item_id,))
            db.execute("DELETE FROM series WHERE title_id=%s", (item_id,))
        result = db.execute(
            sql.SQL("DELETE FROM {} WHERE {}=%s RETURNING {}").format(
                sql.Identifier(table), sql.Identifier(key), sql.Identifier(key)
            ),
            (item_id,),
        ).fetchone()
        if not result:
            raise HTTPException(404, "Record not found.")
    return {"ok": True}
