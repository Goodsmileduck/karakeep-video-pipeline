import httpx
from tagger.logic import parse_tags

PROMPT = ("You are a tagging assistant. Read the video transcript and reply with ONLY "
          "a comma-separated list of 5-12 concise topical tags. No commentary.\n\nTranscript:\n{t}")

def tags_from_transcript(client: httpx.Client, base: str, model: str, transcript: str) -> list[str]:
    r = client.post(base.rstrip("/") + "/api/chat", timeout=300, json={
        "model": model, "stream": False,
        "messages": [{"role": "user", "content": PROMPT.format(t=transcript[:6000])}],
    })
    r.raise_for_status()
    return parse_tags(r.json()["message"]["content"])
