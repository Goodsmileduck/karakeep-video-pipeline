import httpx, pytest
from fetcher.cobalt import download_video, CobaltError

def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))

def test_download_tunnel(tmp_path):
    media = b"FAKEVIDEOBYTES"
    def handler(req):
        if req.url.path == "/" and req.method == "POST":
            assert req.headers["authorization"].startswith("Api-Key ")
            return httpx.Response(200, json={"status": "tunnel", "url": "https://cobalt/media/x.mp4"})
        return httpx.Response(200, content=media)  # the media fetch
    out = download_video(_client(handler), "http://cobalt:9000", "k", "https://tiktok.com/@x/video/1", str(tmp_path/"v.mp4"))
    assert open(out, "rb").read() == media

def test_download_error(tmp_path):
    def handler(req):
        return httpx.Response(200, json={"status": "error", "error": {"code": "fetch.empty"}})
    with pytest.raises(CobaltError):
        download_video(_client(handler), "http://cobalt:9000", "k", "https://tiktok.com/@x/video/1", str(tmp_path/"v.mp4"))
