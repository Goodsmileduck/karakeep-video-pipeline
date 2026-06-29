import json, re

def _tags(bm): return {t.get("name") for t in bm.get("tags", [])}

def needs_tagging(bm: dict, done_tag: str, failed_tag: str | None = None) -> bool:
    tags = _tags(bm)
    if done_tag in tags or (failed_tag and failed_tag in tags):
        return False
    return any(a.get("assetType") == "video" for a in bm.get("assets", []))

def video_asset_id(bm: dict):
    for a in bm.get("assets", []):
        if a.get("assetType") == "video":
            return a.get("id")
    return None

def parse_tags(llm_text: str) -> list[str]:
    s = llm_text.strip()
    s = re.sub(r"^```[a-zA-Z]*\n?|```$", "", s).strip()
    if not s:
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
    except Exception:
        pass
    return [p.strip() for p in re.split(r"[,\n]", s) if p.strip()]

def is_empty_transcript(text: str) -> bool:
    t = re.sub(r"\[.*?\]", "", text, flags=re.I).strip()
    return len(t) < 3
