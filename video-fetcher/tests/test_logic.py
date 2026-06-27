from fetcher.urls import is_video_url
from fetcher.candidates import needs_fetch

def test_is_video_url():
    assert is_video_url("https://www.instagram.com/reel/abc/")
    assert is_video_url("https://www.tiktok.com/@x/video/123")
    assert is_video_url("https://youtu.be/abc")
    assert not is_video_url("https://example.com/article")
    assert not is_video_url("not a url")

def _bm(url, tags=(), assets=()):
    return {"content": {"type": "link", "url": url},
            "tags": [{"name": t} for t in tags],
            "assets": [{"assetType": a} for a in assets]}

def test_needs_fetch():
    # video URL, no video asset, no sentinel -> yes
    assert needs_fetch(_bm("https://tiktok.com/@x/video/1"), "video-fetched", "fetch-failed")
    # already has a video asset -> no
    assert not needs_fetch(_bm("https://tiktok.com/@x/video/1", assets=["video"]), "video-fetched", "fetch-failed")
    # already marked fetched -> no
    assert not needs_fetch(_bm("https://tiktok.com/@x/video/1", tags=["video-fetched"]), "video-fetched", "fetch-failed")
    # marked failed -> no (don't loop)
    assert not needs_fetch(_bm("https://tiktok.com/@x/video/1", tags=["fetch-failed"]), "video-fetched", "fetch-failed")
    # non-video url -> no
    assert not needs_fetch(_bm("https://example.com/x"), "video-fetched", "fetch-failed")
