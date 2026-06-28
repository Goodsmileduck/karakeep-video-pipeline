import pytest
from fetcher.download import download_with_fallback, DownloadError
from fetcher.cobalt import CobaltError
from fetcher.ytdlp import YtdlpError


def test_cobalt_success_skips_ytdlp(tmp_path):
    ytdlp_called = []
    def cobalt_fn(url, path):
        return path
    def ytdlp_fn(url, path):
        ytdlp_called.append(url); return path
    out = download_with_fallback("u", str(tmp_path / "v.mp4"), cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn)
    assert out == str(tmp_path / "v.mp4")
    assert ytdlp_called == []  # cobalt worked → yt-dlp not tried


def test_cobalt_fail_falls_back_to_ytdlp(tmp_path):
    def cobalt_fn(url, path):
        raise CobaltError("cobalt status=error: tiktok")
    def ytdlp_fn(url, path):
        return path  # yt-dlp succeeds
    out = download_with_fallback("u", str(tmp_path / "v.mp4"), cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn)
    assert out == str(tmp_path / "v.mp4")


def test_both_fail_raises_download_error(tmp_path):
    def cobalt_fn(url, path):
        raise CobaltError("cobalt down")
    def ytdlp_fn(url, path):
        raise YtdlpError("yt-dlp down")
    with pytest.raises(DownloadError):
        download_with_fallback("u", str(tmp_path / "v.mp4"), cobalt_fn=cobalt_fn, ytdlp_fn=ytdlp_fn)
