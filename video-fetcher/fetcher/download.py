import logging
import httpx
from fetcher.cobalt import CobaltError
from fetcher.ytdlp import download_video_ytdlp
from fetcher.validate import ensure_video, NotAVideoError

log = logging.getLogger("video-fetcher")


class DownloadError(Exception):
    ...


def download_with_fallback(url: str, path: str, *, cobalt_fn,
                           ytdlp_fn=download_video_ytdlp, validate_fn=ensure_video) -> str:
    """Download `url` to `path`, trying Cobalt first then yt-dlp.

    Cobalt is reliable for Instagram; yt-dlp covers what Cobalt's extractors miss
    (e.g. TikTok) and 1800+ other sites. Raises DownloadError only if BOTH fail.
    `cobalt_fn(url, path)` does the Cobalt download (raising CobaltError/httpx errors).

    Each downloader's output is validated with `validate_fn` (raises NotAVideoError):
    Cobalt can answer status:tunnel yet serve the post's cover JPEG when Instagram
    won't serve the video anonymously. Without this check that image was attached as
    a "video" asset and broke transcription downstream. A non-video result is treated
    exactly like a download failure, so it falls through to yt-dlp (which can use
    cookies) and ultimately to a fetch-failed sentinel rather than a bogus asset.
    """
    try:
        cobalt_fn(url, path)
        validate_fn(path)
        return path
    except (CobaltError, httpx.HTTPError, NotAVideoError) as ce:
        log.warning("cobalt unusable for %s (%s); falling back to yt-dlp", url, ce)
        try:
            ytdlp_fn(url, path)
            validate_fn(path)
            return path
        except Exception as ye:
            raise DownloadError(f"both downloaders failed — cobalt: {ce} ; yt-dlp: {ye}")
