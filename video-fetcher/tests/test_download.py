import pytest
from fetcher.download import download_with_fallback, DownloadError
from fetcher.cobalt import CobaltError
from fetcher.ytdlp import YtdlpError
from fetcher.validate import NotAVideoError


def _ok(path):
    return None  # validate_fn that accepts anything


def _reject(path):
    raise NotAVideoError("cover image")


def test_cobalt_success_skips_ytdlp(tmp_path):
    ytdlp_called = []
    def cobalt_fn(url, path):
        return path
    def ytdlp_fn(url, path):
        ytdlp_called.append(url); return path
    out = download_with_fallback("u", str(tmp_path / "v.mp4"),
                                 cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn, validate_fn=_ok)
    assert out == str(tmp_path / "v.mp4")
    assert ytdlp_called == []  # cobalt worked → yt-dlp not tried


def test_cobalt_fail_falls_back_to_ytdlp(tmp_path):
    def cobalt_fn(url, path):
        raise CobaltError("cobalt status=error: tiktok")
    def ytdlp_fn(url, path):
        return path  # yt-dlp succeeds
    out = download_with_fallback("u", str(tmp_path / "v.mp4"),
                                 cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn, validate_fn=_ok)
    assert out == str(tmp_path / "v.mp4")


def test_both_fail_raises_download_error(tmp_path):
    def cobalt_fn(url, path):
        raise CobaltError("cobalt down")
    def ytdlp_fn(url, path):
        raise YtdlpError("yt-dlp down")
    with pytest.raises(DownloadError):
        download_with_fallback("u", str(tmp_path / "v.mp4"),
                               cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn, validate_fn=_ok)


def test_cobalt_returns_non_video_falls_back_to_ytdlp(tmp_path):
    """Cobalt 'succeeds' but returns a cover image → validation fails → yt-dlp tried."""
    ytdlp_called = []
    def cobalt_fn(url, path):
        return path  # no exception, but it's an image
    def ytdlp_fn(url, path):
        ytdlp_called.append(url); return path
    # validator rejects cobalt's output once, accepts yt-dlp's
    seen = []
    def validate_fn(path):
        seen.append(path)
        if len(seen) == 1:
            raise NotAVideoError("cover image")
        return None
    out = download_with_fallback("u", str(tmp_path / "v.mp4"),
                                 cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn, validate_fn=validate_fn)
    assert out == str(tmp_path / "v.mp4")
    assert ytdlp_called == ["u"]  # fell back because cobalt's file wasn't a video


def test_both_return_non_video_raises_download_error(tmp_path):
    """Cobalt image + yt-dlp also not a video → DownloadError (→ fetch-failed)."""
    def cobalt_fn(url, path):
        return path
    def ytdlp_fn(url, path):
        return path
    with pytest.raises(DownloadError):
        download_with_fallback("u", str(tmp_path / "v.mp4"),
                               cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn, validate_fn=_reject)
