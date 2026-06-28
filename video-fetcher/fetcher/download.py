import logging
import httpx
from fetcher.cobalt import CobaltError
from fetcher.ytdlp import download_video_ytdlp

log = logging.getLogger("video-fetcher")


class DownloadError(Exception):
    ...


def download_with_fallback(url: str, path: str, *, cobalt_fn, ytdlp_fn=download_video_ytdlp) -> str:
    """Download `url` to `path`, trying Cobalt first then yt-dlp.

    Cobalt is reliable for Instagram; yt-dlp covers what Cobalt's extractors miss
    (e.g. TikTok) and 1800+ other sites. Raises DownloadError only if BOTH fail.
    `cobalt_fn(url, path)` does the Cobalt download (raising CobaltError/httpx errors).
    """
    try:
        return cobalt_fn(url, path)
    except (CobaltError, httpx.HTTPError) as ce:
        log.warning("cobalt failed for %s (%s); falling back to yt-dlp", url, ce)
        try:
            return ytdlp_fn(url, path)
        except Exception as ye:
            raise DownloadError(f"both downloaders failed — cobalt: {ce} ; yt-dlp: {ye}")
