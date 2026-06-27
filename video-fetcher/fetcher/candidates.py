from fetcher.urls import is_video_url

def _tag_names(bookmark: dict) -> set[str]:
    return {t.get("name") for t in bookmark.get("tags", [])}

def _asset_types(bookmark: dict) -> set[str]:
    return {a.get("assetType") for a in bookmark.get("assets", [])}

def needs_fetch(bookmark: dict, fetched_tag: str, failed_tag: str) -> bool:
    content = bookmark.get("content", {})
    if content.get("type") != "link" or not is_video_url(content.get("url", "")):
        return False
    if {fetched_tag, failed_tag} & _tag_names(bookmark):
        return False
    if "video" in _asset_types(bookmark):
        return False
    return True
