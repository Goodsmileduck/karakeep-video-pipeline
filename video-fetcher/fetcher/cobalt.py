import httpx

class CobaltError(Exception): ...

def download_video(client: httpx.Client, api_base: str, api_key: str, url: str, dest_path: str) -> str:
    r = client.post(api_base.rstrip("/") + "/",
                    headers={"Authorization": f"Api-Key {api_key}",
                             "Accept": "application/json", "Content-Type": "application/json"},
                    json={"url": url}, timeout=60)
    r.raise_for_status()
    data = r.json()
    status = data.get("status")
    if status in ("tunnel", "redirect", "stream"):
        media_url = data["url"]
    elif status == "picker":
        items = data.get("picker") or []
        if not items:
            raise CobaltError("picker returned no items")
        media_url = items[0]["url"]
    else:
        raise CobaltError(f"cobalt status={status}: {data.get('error')}")
    with client.stream("GET", media_url, timeout=600) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return dest_path
