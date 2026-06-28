import pytest
from fetcher.ytdlp import download_video_ytdlp, YtdlpError


class _Proc:
    def __init__(self, rc, err=""):
        self.returncode = rc
        self.stderr = err
        self.stdout = ""


def test_ytdlp_success(tmp_path):
    calls = []
    def runner(cmd, **kw):
        calls.append(cmd)
        return _Proc(0)
    out = download_video_ytdlp("https://www.tiktok.com/@x/video/1", str(tmp_path / "v.mp4"), runner=runner)
    assert out == str(tmp_path / "v.mp4")
    assert calls[0][0] == "yt-dlp"
    assert str(tmp_path / "v.mp4") in calls[0]
    assert "https://www.tiktok.com/@x/video/1" in calls[0]


def test_ytdlp_failure_raises(tmp_path):
    def runner(cmd, **kw):
        return _Proc(1, "ERROR: Unable to extract")
    with pytest.raises(YtdlpError):
        download_video_ytdlp("https://www.tiktok.com/@x/video/1", str(tmp_path / "v.mp4"), runner=runner)


def test_ytdlp_adds_cookies_when_env_file_exists(tmp_path, monkeypatch):
    cookies = tmp_path / "instagram.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n")
    monkeypatch.setenv("YTDLP_COOKIES", str(cookies))
    calls = []
    def runner(cmd, **kw):
        calls.append(cmd)
        return _Proc(0)
    download_video_ytdlp("https://www.instagram.com/reel/X/", str(tmp_path / "v.mp4"), runner=runner)
    assert "--cookies" in calls[0]
    assert str(cookies) == calls[0][calls[0].index("--cookies") + 1]


def test_ytdlp_omits_cookies_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("YTDLP_COOKIES", raising=False)
    calls = []
    def runner(cmd, **kw):
        calls.append(cmd)
        return _Proc(0)
    download_video_ytdlp("https://www.tiktok.com/@x/video/1", str(tmp_path / "v.mp4"), runner=runner)
    assert "--cookies" not in calls[0]


def test_ytdlp_omits_cookies_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("YTDLP_COOKIES", str(tmp_path / "nope.txt"))
    calls = []
    def runner(cmd, **kw):
        calls.append(cmd)
        return _Proc(0)
    download_video_ytdlp("https://www.instagram.com/reel/X/", str(tmp_path / "v.mp4"), runner=runner)
    assert "--cookies" not in calls[0]
