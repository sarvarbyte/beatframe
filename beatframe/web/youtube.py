"""YouTube upload through the official Data API (OAuth, your own Google Cloud project).

Setup once:
  1. console.cloud.google.com -> new project -> enable "YouTube Data API v3"
  2. OAuth consent screen: External, add yourself as a test user
  3. Credentials -> Create OAuth client ID -> type "Desktop app" -> download JSON
  4. Save it as ~/.beatframe/client_secret.json, then press "Connect YouTube" in the app

Note: until the Google Cloud project passes YouTube's API audit, every video uploaded
through the API is locked to Private. The app still uploads (handy for drafts), and the
"manual upload" panel always works.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

CONFIG_DIR = Path(os.environ.get("BEATFRAME_HOME", Path.home() / ".beatframe"))
CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
TOKEN = CONFIG_DIR / "youtube_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",   # captions
    "https://www.googleapis.com/auth/youtube.readonly",    # channel name
]

os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # loopback http://127.0.0.1 only
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

_pending: dict[str, object] = {}   # state -> Flow (keeps the PKCE verifier between redirects)


def is_configured() -> bool:
    return CLIENT_SECRET.exists()


def _creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds if creds and creds.valid else None


def is_connected() -> bool:
    try:
        return _creds() is not None
    except Exception:  # noqa: BLE001
        return False


def channel_name() -> str:
    try:
        from googleapiclient.discovery import build

        yt = build("youtube", "v3", credentials=_creds(), cache_discovery=False)
        items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
        return items[0]["snippet"]["title"] if items else ""
    except Exception:  # noqa: BLE001
        return ""


def auth_url(redirect_uri: str) -> str:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(str(CLIENT_SECRET), scopes=SCOPES, redirect_uri=redirect_uri)
    url, state = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    _pending[state] = flow
    return url


def finish(state: str, full_url: str) -> None:
    flow = _pending.pop(state, None)
    if flow is None:
        raise RuntimeError("login session expired, press Connect again")
    flow.fetch_token(authorization_response=full_url)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(flow.credentials.to_json(), encoding="utf-8")


def disconnect() -> None:
    TOKEN.unlink(missing_ok=True)


def upload(
    video: Path,
    meta: dict,
    log: Callable[[str], None],
    progress: Callable[[float], None],
    captions: Path | None = None,
    thumbnail: Path | None = None,
) -> dict:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = _creds()
    if not creds:
        raise RuntimeError("YouTube is not connected")
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    status = {
        "privacyStatus": meta.get("privacy", "private"),
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": bool(meta.get("synthetic", False)),
    }
    if meta.get("publish_at"):
        # publishAt only works for private videos; YouTube makes them public at that time
        status["privacyStatus"] = "private"
        status["publishAt"] = meta["publish_at"]

    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta.get("description", "")[:5000],
            "tags": meta.get("tags", [])[:30],
            "categoryId": meta.get("category", "27"),   # 27 = Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status,
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    log(f"uploading {video.name} ({video.stat().st_size / 1e6:.1f} MB)")
    resp = None
    while resp is None:
        st, resp = req.next_chunk()
        if st:
            progress(st.progress() * 0.9)
    vid = resp["id"]
    log(f"uploaded: https://youtu.be/{vid}")
    result = {"id": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
              "privacy": resp.get("status", {}).get("privacyStatus", ""), "warnings": []}

    if captions and captions.exists():
        try:
            yt.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": vid, "language": "en", "name": "English", "isDraft": False}},
                media_body=MediaFileUpload(str(captions), mimetype="application/octet-stream"),
            ).execute()
            log("subtitles added")
        except Exception as e:  # noqa: BLE001
            result["warnings"].append(f"subtitles: {e}")
            log(f"subtitles skipped: {e}")
    if thumbnail and thumbnail.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail))).execute()
            log("thumbnail set")
        except Exception as e:  # noqa: BLE001
            msg = "custom thumbnails need a phone-verified channel" if "forbidden" in str(e).lower() else str(e)
            result["warnings"].append(f"thumbnail: {msg}")
            log(f"thumbnail skipped: {msg}")
    progress(1.0)
    return result


def to_rfc3339(local_value: str, tz_offset_minutes: int) -> str:
    """'2026-10-05T18:30' from <input type=datetime-local> + browser offset -> UTC RFC3339."""
    dt = datetime.fromisoformat(local_value)
    from datetime import timedelta

    utc = dt + timedelta(minutes=tz_offset_minutes)
    return utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def secret_info() -> dict:
    if not is_configured():
        return {}
    try:
        data = json.loads(CLIENT_SECRET.read_text())
        kind = "installed" if "installed" in data else ("web" if "web" in data else "?")
        return {"kind": kind, "project": (data.get(kind) or {}).get("project_id", "")}
    except Exception:  # noqa: BLE001
        return {"kind": "invalid"}
