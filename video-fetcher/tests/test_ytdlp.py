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
