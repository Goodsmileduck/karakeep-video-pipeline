from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

# Query params that are pure tracking noise: they identify a share/click, not the
# content. Instagram appends igsh/igshid/_t/_r on "copy link"; utm_* is generic
# analytics. Cobalt rejects some of these with a 400, and they never help extraction.
_DROP_EXACT = {"igsh", "igshid", "_t", "_r"}
_DROP_PREFIX = ("utm_",)


def _is_tracker(key: str) -> bool:
    return key in _DROP_EXACT or key.startswith(_DROP_PREFIX)


def clean_url(url: str) -> str:
    """Strip known tracking query params, preserving path, real params, and fragment.

    Non-URL input (no scheme/host) is returned unchanged.
    """
    try:
        parts = urlparse(url)
    except Exception:
        return url
    if not parts.scheme or not parts.netloc:
        return url
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracker(k)]
    return urlunparse(parts._replace(query=urlencode(kept)))
