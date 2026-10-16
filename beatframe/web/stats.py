"""Channel statistics as one compact text block, to paste into a Claude chat.

Uses the same OAuth login as uploads (CONFIG_DIR), so every Beatframe copy reads only
the channel it is connected to. Needs two things once:
  * "YouTube Analytics API" enabled in the same Google Cloud project as the Data API
  * the yt-analytics.readonly scope -> press "Reconnect YouTube" on the Stats page

YouTube's API does not expose thumbnail impressions or impressions CTR; those stay in Studio.
Analytics numbers lag about 2 days behind Studio's realtime view.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

from beatframe.web import youtube

ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
LAST = youtube.CONFIG_DIR / "stats_last.txt"
SHORT_MAX_SECONDS = 180   # YouTube treats vertical videos up to 3 min as Shorts


class StatsError(RuntimeError):
    """A problem the page should explain in plain words (not a crash)."""


def has_scope() -> bool:
    """True when the saved login already allows reading YouTube Analytics."""
    try:
        data = json.loads(youtube.TOKEN.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    scopes = data.get("scopes") or data.get("scope") or []
    if isinstance(scopes, str):
        scopes = scopes.split()
    return ANALYTICS_SCOPE in scopes


def last_report() -> dict:
    if not LAST.exists():
        return {}
    return {"text": LAST.read_text(encoding="utf-8"),
            "when": datetime.fromtimestamp(LAST.stat().st_mtime).strftime("%d %b %H:%M")}


# ----------------------------------------------------------------- helpers
def _secs(iso: str) -> int:
    """ISO-8601 duration (PT1M5S) -> seconds."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def _mmss(s: float | int | None) -> str:
    s = int(round(s or 0))
    return f"{s // 60}:{s % 60:02d}"


def _age(published: datetime, now: datetime) -> str:
    h = (now - published).total_seconds() / 3600
    return f"{int(h)}h" if h < 48 else f"{int(h // 24)}d"


TRAFFIC_NAMES = {
    "SHORTS": "Shorts feed", "YT_SEARCH": "YouTube search", "RELATED_VIDEO": "Suggested", "SUBSCRIBER": "Browse/home",
    "YT_CHANNEL": "Channel page", "YT_OTHER_PAGE": "Other YouTube", "EXT_URL": "External", "NO_LINK_OTHER": "Direct/unknown",
    "PLAYLIST": "Playlists", "YT_PLAYLIST_PAGE": "Playlist page", "NOTIFICATION": "Notifications", "END_SCREEN": "End screens",
    "HASHTAGS": "Hashtags", "SOUND_PAGE": "Sound page",
}


def _n(x) -> str:
    return f"{int(x):,}" if x is not None else "-"


def _query(ya, **kw) -> list[dict]:
    """Run an Analytics query and return rows as dicts."""
    res = ya.reports().query(ids="channel==MINE", **kw).execute()
    cols = [c["name"] for c in res.get("columnHeaders", [])]
    return [dict(zip(cols, r)) for r in res.get("rows", []) or []]


def _per_video(ya, start: str, end: str) -> tuple[dict, bool]:
    """Lifetime numbers per video. engagedViews is newer; fall back without it if refused."""
    base = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,subscribersGained"
    for metrics, engaged in ((base + ",engagedViews", True), (base, False)):
        try:
            rows = _query(ya, startDate=start, endDate=end, metrics=metrics, dimensions="video",
                          sort="-views", maxResults=200)
            return {r["video"]: r for r in rows}, engaged
        except Exception as e:  # noqa: BLE001
            if engaged and "engagedViews" in str(e):
                continue
            raise
    return {}, False


# ------------------------------------------------------------------ report
def build_report(days: int = 28, max_videos: int = 60) -> str:
    """Fetch the connected channel's numbers and return the text block."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    creds = youtube._creds()  # noqa: SLF001
    if not creds:
        raise StatsError("YouTube is not connected. Press Connect YouTube first.")
    if not has_scope():
        raise StatsError("The YouTube login does not allow statistics yet. Press Reconnect YouTube.")

    try:
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

        ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute().get("items", [])
        if not ch:
            raise StatsError("This Google account has no YouTube channel.")
        ch = ch[0]
        cid, title = ch["id"], ch["snippet"]["title"]
        subs = ch.get("statistics", {}).get("subscriberCount", "?")
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        created = ch["snippet"]["publishedAt"][:10]

        # newest uploads first
        ids, token = [], None
        while len(ids) < max_videos:
            r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50,
                                        pageToken=token).execute()
            ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
            token = r.get("nextPageToken")
            if not token:
                break
        ids = ids[:max_videos]
        videos = []
        for k in range(0, len(ids), 50):
            videos += yt.videos().list(part="snippet,contentDetails,statistics,status",
                                       id=",".join(ids[k:k + 50])).execute().get("items", [])

        today = date.today()
        end = today.isoformat()
        start = (today - timedelta(days=days)).isoformat()
        per, engaged = _per_video(ya, created, end)
        tot = _query(ya, startDate=start, endDate=end,
                     metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost")
        traffic = _query(ya, startDate=start, endDate=end, metrics="views",
                         dimensions="insightTrafficSourceType", sort="-views")
    except StatsError:
        raise
    except HttpError as e:
        msg = str(e)
        if "accessNotConfigured" in msg or "has not been used" in msg or "disabled" in msg:
            raise StatsError("Turn on \"YouTube Analytics API\" in your Google Cloud project "
                             "(APIs & Services → Library), wait a minute, then try again.") from e
        if "insufficient" in msg.lower() or "403" in msg:
            raise StatsError("YouTube refused the request. Press Reconnect YouTube and allow statistics.") from e
        raise StatsError(f"YouTube API error: {msg[:300]}") from e

    now = datetime.now(timezone.utc)
    lines = [
        f"CHANNEL: {title} ({cid}) · subscribers {subs} · report {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "SOURCE: YouTube Analytics API (about 2 days behind Studio realtime; impressions/CTR are not in the API)",
    ]
    if tot:
        t = tot[0]
        lines.append(f"LAST {days} DAYS: views {_n(t.get('views'))} · watch {t.get('estimatedMinutesWatched', 0) / 60:.1f} h"
                     f" · subs +{int(t.get('subscribersGained', 0))} / -{int(t.get('subscribersLost', 0))}")
    if traffic:
        total = sum(r["views"] for r in traffic) or 1
        parts = [f"{TRAFFIC_NAMES.get(r['insightTrafficSourceType'], r['insightTrafficSourceType'].replace('_', ' ').title())}"
                 f" {100 * r['views'] / total:.0f}%"
                 for r in traffic[:6]]
        lines.append("TRAFFIC (views): " + " · ".join(parts))

    head = "type | published | age | length | title | views | " + ("engaged | " if engaged else "") + \
           "avg view | % viewed | likes | comments | subs | status"
    lines += ["", "VIDEOS (newest first, lifetime):", head]
    for v in videos:
        sn, st, cd, stt = v["snippet"], v.get("statistics", {}), v["contentDetails"], v.get("status", {})
        secs = _secs(cd.get("duration", ""))
        pub = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        a = per.get(v["id"], {})
        row = [
            "S" if secs and secs <= SHORT_MAX_SECONDS else "L",
            pub.strftime("%Y-%m-%d"), _age(pub, now), _mmss(secs), sn["title"][:70],
            _n(st.get("viewCount")),
        ]
        if engaged:
            row.append(_n(a.get("engagedViews")) if a else "-")
        row += [
            _mmss(a.get("averageViewDuration")) if a else "-",
            f"{a['averageViewPercentage']:.1f}%" if a.get("averageViewPercentage") is not None else "-",
            _n(st.get("likeCount")), _n(st.get("commentCount")),
            f"+{int(a.get('subscribersGained', 0))}" if a else "-",
            stt.get("privacyStatus", "?").upper() if stt.get("privacyStatus") != "public" else "public",
        ]
        lines.append(" | ".join(row))
    if any(v.get("status", {}).get("privacyStatus") == "private" for v in videos):
        lines.append("NOTE: PRIVATE videos get no impressions — set them to Public in Studio if they should be live.")
    lines.append("(S = up to 3 min, treated as a Short. Videos under ~2 days old may show '-' in analytics columns.)")

    text = "\n".join(lines)
    youtube.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LAST.write_text(text, encoding="utf-8")
    return text
