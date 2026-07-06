from .. import config


def fetch(url: str) -> tuple[str, str]:
    """用 yt-dlp 抓 IG Reels 的 caption/metadata(不下載影片)。
    IG 常要求登入,失敗時由上層降級處理。"""
    import yt_dlp  # 延遲 import,沒裝也不影響其他 adapter

    opts = {"skip_download": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title") or "IG Reels"
    desc = info.get("description") or ""
    uploader = info.get("uploader") or info.get("channel") or "?"
    if not desc and not info.get("title"):
        raise ValueError("抓不到文案(IG 可能要求登入)")

    content = (
        f"Instagram Reels\n作者: {uploader}\n標題: {title}\n\n文案:\n{desc}"
    )
    return title, content[: config.MAX_CONTENT_CHARS]
