import httpx
from fetcher.karakeep import KarakeepClient

def test_attach_and_tag(tmp_path):
    calls = []
    def handler(req):
        calls.append((req.method, req.url.path))
        if req.url.path == "/api/v1/assets":
            return httpx.Response(200, json={"assetId": "A1", "contentType": "video/mp4"})
        if req.url.path.endswith("/assets"):   # attach
            return httpx.Response(200, json={"ok": True})
        if req.url.path.endswith("/tags"):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)
    c = KarakeepClient("http://k/api/v1", "tok", client=httpx.Client(transport=httpx.MockTransport(handler)))
    p = tmp_path/"v.mp4"; p.write_bytes(b"x")
    asset_id = c.upload_asset(str(p), "video/mp4")
    c.attach_asset("B1", asset_id)
    c.add_tag("B1", "video-fetched")
    assert ("POST", "/api/v1/assets") in calls
    assert ("POST", "/api/v1/bookmarks/B1/assets") in calls
    assert ("POST", "/api/v1/bookmarks/B1/tags") in calls
