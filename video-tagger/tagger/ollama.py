import httpx
from tagger.logic import parse_tags

PROMPT = (
    "You are a tagging assistant. Read the video transcript and bookmark metadata. "
    "Reply with ONLY a comma-separated list of 5-12 concise topical tags. "
    "Do not include raw hashtags, concatenated hashtag blocks, very long tags, or commentary.\n\n"
    "{content}"
)


def tags_from_content(client: httpx.Client, base: str, model: str, content: str) -> list[str]:
    r = client.post(
        base.rstrip("/") + "/api/chat",
        timeout=300,
        json={
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": PROMPT.format(content=content[:6000])}],
        },
    )
    r.raise_for_status()
    return parse_tags(r.json()["message"]["content"])
