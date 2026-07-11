import httpx

from .. import config


def fetch(url: str) -> tuple[str, str, str | None]:
    """yt-dlp 抓 YouTube metadata + 字幕(不下載影片)。"""
    import yt_dlp

    opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title") or "YouTube 影片"
    uploader = info.get("uploader") or info.get("channel") or "?"
    desc = (info.get("description") or "").strip()[:2000]
    dur = info.get("duration") or 0
    transcript = _caption_text(info)

    content = (
        f"YouTube 影片\n作者: {uploader}\n標題: {title}\n"
        f"長度: {dur // 60} 分 {dur % 60} 秒\n\n"
        f"說明欄:\n{desc or '(空)'}\n\n"
        f"字幕逐字稿:\n{transcript or '(無字幕,只能靠說明欄摘要)'}"
    )
    # YouTube CC 影片 yt-dlp 會回 "Creative Commons Attribution license (reuse allowed)"
    license_ = info.get("license")
    if license_ and "creative commons" in license_.lower():
        license_ = "CC-BY"
    return title, content[: config.MAX_CONTENT_CHARS], license_


def _pick_track(d: dict | None):
    if not d:
        return None
    for pref in ("zh-Hant", "zh-TW", "zh", "en"):
        for lang, tracks in d.items():
            if lang.startswith(pref) and tracks:
                return tracks
    return next(iter(d.values()), None)


def _caption_text(info: dict) -> str:
    tracks = _pick_track(info.get("subtitles")) or _pick_track(
        info.get("automatic_captions")
    )
    if not tracks:
        return ""
    track = next((t for t in tracks if t.get("ext") == "json3"), tracks[0])
    try:
        r = httpx.get(track["url"], timeout=30, follow_redirects=True)
        r.raise_for_status()
        if track.get("ext") == "json3":
            return parse_json3(r.json())
        return parse_vtt(r.text)
    except Exception:  # noqa: BLE001
        return ""


def parse_json3(data: dict) -> str:
    segs = []
    for ev in data.get("events") or []:
        for s in ev.get("segs") or []:
            text = s.get("utf8", "")
            if text.strip():
                segs.append(text)
    return "".join(segs).strip()


def parse_vtt(text: str) -> str:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if (
            not line
            or "-->" in line
            or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE"))
            or line.isdigit()
        ):
            continue
        if not out or out[-1] != line:
            out.append(line)
    return " ".join(out).strip()
