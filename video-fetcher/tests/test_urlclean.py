from fetcher.urlclean import clean_url


def test_strips_instagram_tracking_params():
    assert (
        clean_url("https://www.instagram.com/reel/X/?utm_source=ig_web_copy_link&igsh=abc")
        == "https://www.instagram.com/reel/X/"
    )


def test_strips_all_known_trackers_keeps_real_params():
    url = "https://www.instagram.com/reel/X/?utm_medium=share&igshid=1&_t=2&_r=3&foo=bar"
    assert clean_url(url) == "https://www.instagram.com/reel/X/?foo=bar"


def test_no_query_unchanged():
    assert clean_url("https://www.tiktok.com/@x/video/1") == "https://www.tiktok.com/@x/video/1"


def test_preserves_path_and_fragment():
    assert (
        clean_url("https://youtu.be/abc?utm_source=x&t=30")
        == "https://youtu.be/abc?t=30"
    )


def test_non_url_returned_unchanged():
    assert clean_url("not a url") == "not a url"
    assert clean_url("") == ""
