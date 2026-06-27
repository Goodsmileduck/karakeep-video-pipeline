import httpx

class KarakeepClient:
    def __init__(self, base, token, client=None):
        self.base = base.rstrip("/")
        self.h = {"Authorization": f"Bearer {token}"}
        self.c = client or httpx.Client(timeout=120)

    def list_recent(self, limit=50):
        r = self.c.get(f"{self.base}/bookmarks", headers=self.h, params={"limit": limit})
        r.raise_for_status()
        return r.json().get("bookmarks", [])

    def upload_asset(self, path, mime):
        with open(path, "rb") as f:
            r = self.c.post(f"{self.base}/assets", headers=self.h,
                            files={"file": (path.split("/")[-1], f, mime)})
        r.raise_for_status()
        return r.json()["assetId"]

    def attach_asset(self, bookmark_id, asset_id, asset_type="video"):
        r = self.c.post(f"{self.base}/bookmarks/{bookmark_id}/assets", headers=self.h,
                        json={"id": asset_id, "assetType": asset_type})
        r.raise_for_status()

    def add_tag(self, bookmark_id, tag):
        r = self.c.post(f"{self.base}/bookmarks/{bookmark_id}/tags", headers=self.h,
                        json={"tags": [{"tagName": tag}]})
        r.raise_for_status()
