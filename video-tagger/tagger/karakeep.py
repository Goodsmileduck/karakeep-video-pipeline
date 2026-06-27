import httpx

class KarakeepClient:
    def __init__(self, base, token, client=None):
        self.base = base.rstrip("/"); self.h = {"Authorization": f"Bearer {token}"}
        self.c = client or httpx.Client(timeout=300)
    def list_recent(self, limit=50):
        r = self.c.get(f"{self.base}/bookmarks", headers=self.h, params={"limit": limit})
        r.raise_for_status(); return r.json().get("bookmarks", [])
    def get_asset_bytes(self, asset_id, dest):
        with self.c.stream("GET", f"{self.base}/assets/{asset_id}", headers=self.h) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for ch in r.iter_bytes(): f.write(ch)
        return dest
    def add_tag(self, bid, tag):
        r = self.c.post(f"{self.base}/bookmarks/{bid}/tags", headers=self.h,
                        json={"tags":[{"tagName": tag}]}); r.raise_for_status()
    def add_tags(self, bid, tags):
        if tags:
            r = self.c.post(f"{self.base}/bookmarks/{bid}/tags", headers=self.h,
                            json={"tags":[{"tagName": t} for t in tags]}); r.raise_for_status()
    def set_note(self, bid, note):
        r = self.c.patch(f"{self.base}/bookmarks/{bid}", headers=self.h, json={"note": note})
        r.raise_for_status()
