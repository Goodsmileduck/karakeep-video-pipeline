from urllib.parse import urlparse

VIDEO_HOSTS = ("instagram.com", "tiktok.com", "youtube.com", "youtu.be")

def is_video_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    host = host[4:] if host.startswith("www.") else host
    return any(host == h or host.endswith("." + h) for h in VIDEO_HOSTS)
