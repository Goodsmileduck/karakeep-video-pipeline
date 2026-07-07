import json
import re

MAX_TAG_LEN = 32
MAX_SINGLE_TOKEN_LEN = 24


class TagParseError(Exception):
    def __init__(self, raw_output: str):
        super().__init__("tag parser produced no usable tags")
        self.raw_output = raw_output

def _tags(bm): return {t.get("name") for t in bm.get("tags", [])}

def needs_tagging(bm: dict, done_tag: str) -> bool:
    if done_tag in _tags(bm):
        return False
    return any(a.get("assetType") == "video" for a in bm.get("assets", []))

def video_asset_id(bm: dict):
    for a in bm.get("assets", []):
        if a.get("assetType") == "video":
            return a.get("id")
    return None


def _clean_fence(text: str) -> str:
    s = text.strip()
    s = re.sub(r"^```\s*[a-zA-Z]*\s*\n?|```$", "", s).strip()
    return s


def _raw_tag_candidates(llm_text: str) -> list[str]:
    s = _clean_fence(llm_text)
    if not s:
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
    except Exception:
        pass
    return [p.strip() for p in re.split(r"[,\n]", s) if p.strip()]


def _normalize_tag(tag: str) -> str:
    return re.sub(r"\s+", " ", tag.strip().lstrip("#")).strip()


def _is_bad_tag(tag: str) -> bool:
    if not tag or len(tag) > MAX_TAG_LEN:
        return True
    if len(tag) > MAX_SINGLE_TOKEN_LEN and not re.search(r"[\s_-]", tag):
        return True
    return False


def _split_hashtags(candidate: str) -> list[str]:
    # fused hashtag blocks like "#fitness#yoga" carry real tags — recover them
    return [p for p in candidate.split("#") if p.strip()] if "#" in candidate else [candidate]


def parse_tags(llm_text: str) -> list[str]:
    candidates = _raw_tag_candidates(llm_text)
    seen = set()
    tags = []
    for raw in candidates:
        for part in _split_hashtags(raw):
            tag = _normalize_tag(part)
            if _is_bad_tag(tag):
                continue
            key = tag.casefold()
            if key in seen:
                continue
            seen.add(key)
            tags.append(tag)
    if candidates and not tags:
        raise TagParseError(llm_text)
    return tags


def _metadata_value(content: dict, key: str) -> str:
    value = content.get(key)
    if value is None:
        return ""
    return str(value).strip()


# (label, content key, counts as tagging signal) — URL alone is not enough to tag on.
_CONTEXT_FIELDS = (
    ("Title", "title", True),
    ("Description", "description", True),
    ("Page Text", "text", True),
    ("URL", "url", False),
)


def _context_sections(bm: dict, transcript: str) -> list[tuple[str, str, bool]]:
    sections = []
    transcript = (transcript or "").strip()
    if transcript:
        sections.append(("Transcript", transcript, not is_empty_transcript(transcript)))
    content = bm.get("content", {}) or {}
    for label, key, is_signal in _CONTEXT_FIELDS:
        value = _metadata_value(content, key)
        if value:
            sections.append((label, value, is_signal))
    return sections


def has_tagging_signal(bm: dict, transcript: str) -> bool:
    return any(is_signal for _, _, is_signal in _context_sections(bm, transcript))


def build_tagging_context(bm: dict, transcript: str) -> str:
    return "\n\n".join(f"{label}:\n{value}" for label, value, _ in _context_sections(bm, transcript))


def is_empty_transcript(text: str) -> bool:
    t = re.sub(r"\[.*?\]", "", text, flags=re.I).strip()
    return len(t) < 3
