"""Tests for ensure_video — guards against Cobalt returning a cover image.

Cobalt sometimes answers an Instagram reel with status:tunnel but serves the
post's cover JPEG (when IG won't serve the video anonymously). A still image
probes as a single video stream (mjpeg) with no audio and no duration, so we
reject anything without a real, timed video stream.
"""
import json
from types import SimpleNamespace

import pytest

from fetcher.validate import ensure_video, NotAVideoError


def _runner(streams, duration, rc=0, stderr=""):
    payload = {"streams": streams, "format": {}}
    if duration is not None:
        payload["format"]["duration"] = duration

    def run(cmd, capture_output=True, text=True, timeout=None):
        return SimpleNamespace(returncode=rc, stdout=json.dumps(payload), stderr=stderr)

    return run


def test_real_video_passes(tmp_path):
    p = str(tmp_path / "v.mp4")
    runner = _runner(
        [{"codec_type": "video"}, {"codec_type": "audio"}], "12.3"
    )
    assert ensure_video(p, runner=runner) == p


def test_silent_video_passes(tmp_path):
    """A video with no audio track is still a video if it has a duration."""
    p = str(tmp_path / "v.mp4")
    runner = _runner([{"codec_type": "video"}], "8.0")
    assert ensure_video(p, runner=runner) == p


def test_cover_image_rejected(tmp_path):
    """JPEG cover: one video (mjpeg) stream, no audio, no duration → reject."""
    p = str(tmp_path / "v.mp4")
    runner = _runner([{"codec_type": "video"}], None)
    with pytest.raises(NotAVideoError):
        ensure_video(p, runner=runner)


def test_no_video_stream_rejected(tmp_path):
    p = str(tmp_path / "v.mp4")
    runner = _runner([{"codec_type": "audio"}], "5.0")
    with pytest.raises(NotAVideoError):
        ensure_video(p, runner=runner)


def test_ffprobe_failure_rejected(tmp_path):
    p = str(tmp_path / "v.mp4")
    runner = _runner([], None, rc=1, stderr="Invalid data found")
    with pytest.raises(NotAVideoError):
        ensure_video(p, runner=runner)
