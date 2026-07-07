# Video Tagger Metadata Russian Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve `video-tagger` so it tags from transcripts plus Karakeep metadata, supports forced Russian transcription, logs parse failures, and filters bad hashtag-style tags.

**Architecture:** Keep the pipeline shape unchanged: `tagger.main.process()` downloads the asset, `tagger.transcribe.transcribe()` extracts speech, `tagger.ollama` asks Ollama for tags, and `tagger.logic` owns pure parsing/context helpers. Add one retryable parse error type so invalid model output does not mark a bookmark `transcribed`.

**Tech Stack:** Python, pytest, httpx MockTransport, faster-whisper, Ollama chat API, Docker Compose environment variables.

---

## File Structure

- Modify `video-tagger/tagger/transcribe.py`: add optional language configuration and detected-language logging.
- Modify `video-tagger/tests/test_transcribe.py`: cover `WHISPER_LANGUAGE=ru` and default auto behavior.
- Modify `video-tagger/tagger/logic.py`: add metadata/context helpers, useful-signal detection, tag cleanup, and `TagParseError`.
- Modify `video-tagger/tests/test_logic.py`: cover metadata context and hashtag filtering.
- Modify `video-tagger/tagger/ollama.py`: change prompt from transcript-only to content-based tagging, raise `TagParseError` for unusable non-empty output, keep a compatibility wrapper.
- Modify `video-tagger/tests/test_ollama.py`: cover content prompt and parse failure.
- Modify `video-tagger/tagger/main.py`: use metadata context, tag no-speech items with useful metadata, catch parse failures, and write richer notes.
- Modify `video-tagger/tests/test_main.py`: cover metadata flow, no-speech metadata flow, and parse-failure retry behavior.
- Modify `docker-compose.yml`: document/pass `WHISPER_LANGUAGE`.
- Modify `README.md`: mention metadata-aware tagging, `WHISPER_LANGUAGE`, and parse-error logs.

---

### Task 1: Add Whisper Language Configuration

**Files:**
- Modify: `video-tagger/tagger/transcribe.py`
- Test: `video-tagger/tests/test_transcribe.py`

- [ ] **Step 1: Write failing tests for language options**

Append these tests to `video-tagger/tests/test_transcribe.py`:

```python
class _CapturingModel:
    def __init__(self):
        self.kw = None

    def transcribe(self, path, **kw):
        self.kw = kw
        class _Info:
            language = "ru"
            language_probability = 0.97
            duration = 1.0
        return [_Seg("privet")], _Info()


def test_transcribe_forces_configured_language(tmp_path, monkeypatch):
    monkeypatch.setenv("WHISPER_LANGUAGE", "ru")
    model = _CapturingModel()
    (tmp_path / "v.mp4").write_bytes(b"x")

    assert transcribe(str(tmp_path / "v.mp4"), model=model) == "privet"
    assert model.kw["language"] == "ru"


def test_transcribe_auto_language_omits_language_option(tmp_path, monkeypatch):
    monkeypatch.setenv("WHISPER_LANGUAGE", "auto")
    model = _CapturingModel()
    (tmp_path / "v.mp4").write_bytes(b"x")

    assert transcribe(str(tmp_path / "v.mp4"), model=model) == "privet"
    assert "language" not in model.kw
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd video-tagger && pytest tests/test_transcribe.py -v
```

Expected: the new tests fail because `transcribe()` does not pass `language`.

- [ ] **Step 3: Implement language option and logging**

Replace `video-tagger/tagger/transcribe.py` with:

```python
import logging
import os

log = logging.getLogger("video-tagger")
_model = None


def _default_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            os.environ.get("WHISPER_MODEL", "small"),
            device="cpu",
            compute_type="int8",
        )
    return _model


def _transcribe_options() -> dict:
    language = os.environ.get("WHISPER_LANGUAGE", "").strip()
    if language and language.lower() != "auto":
        return {"language": language}
    return {}


def transcribe(video_path: str, *, model=None, workdir=None) -> str:
    m = model or _default_model()
    segments, info = m.transcribe(video_path, **_transcribe_options())
    detected = getattr(info, "language", None)
    probability = getattr(info, "language_probability", None)
    if detected:
        log.info("whisper detected language=%s probability=%s", detected, probability)
    return " ".join(s.text.strip() for s in segments).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd video-tagger && pytest tests/test_transcribe.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add video-tagger/tagger/transcribe.py video-tagger/tests/test_transcribe.py
git commit -m "feat(tagger): configure whisper language"
```

---

### Task 2: Add Metadata Context and Tag Cleanup Helpers

**Files:**
- Modify: `video-tagger/tagger/logic.py`
- Test: `video-tagger/tests/test_logic.py`

- [ ] **Step 1: Write failing tests for context and cleanup**

Update the import in `video-tagger/tests/test_logic.py`:

```python
from tagger.logic import (
    TagParseError,
    build_tagging_context,
    has_tagging_signal,
    is_empty_transcript,
    needs_tagging,
    parse_tags,
    raw_tag_candidates,
    video_asset_id,
)
```

Append these tests:

```python
def test_build_tagging_context_includes_instagram_metadata():
    bm = {
        "content": {
            "url": "https://www.instagram.com/reel/abc/",
            "title": "Morning mobility reel",
            "description": "Russian caption about yoga, stretching, and recovery",
            "text": "Extra page text",
        }
    }

    context = build_tagging_context(bm, "spoken transcript")

    assert "Transcript:\nspoken transcript" in context
    assert "Title:\nMorning mobility reel" in context
    assert "Description:\nRussian caption about yoga, stretching, and recovery" in context
    assert "Page Text:\nExtra page text" in context
    assert "URL:\nhttps://www.instagram.com/reel/abc/" in context


def test_build_tagging_context_omits_empty_sections():
    context = build_tagging_context({"content": {"url": "https://x.test"}}, "")

    assert "Transcript:" not in context
    assert "Title:" not in context
    assert "URL:\nhttps://x.test" in context


def test_has_tagging_signal_requires_speech_or_useful_metadata():
    assert has_tagging_signal({"content": {"url": "https://x.test"}}, "") is False
    assert has_tagging_signal({"content": {"description": "caption about yoga"}}, "") is True
    assert has_tagging_signal({"content": {"url": "https://x.test"}}, "hello there") is True


def test_parse_tags_normalizes_and_filters_bad_hashtags():
    assert parse_tags(
        "#Yoga, #Fitness, yoga, "
        "#fitnessexerciseweightlossmetabolismyogaenergybooststressrelief"
    ) == ["Yoga", "Fitness"]


def test_parse_tags_preserves_existing_valid_formats():
    assert parse_tags("```json\n[\"Cooking\", \"Recipe\"]\n```") == ["Cooking", "Recipe"]
    assert parse_tags("Cooking\nRecipe\nDessert") == ["Cooking", "Recipe", "Dessert"]


def test_raw_tag_candidates_reports_non_empty_bad_output():
    assert raw_tag_candidates("#fitnessexerciseweightlossmetabolismyogaenergyboost") == [
        "#fitnessexerciseweightlossmetabolismyogaenergyboost"
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd video-tagger && pytest tests/test_logic.py -v
```

Expected: tests fail because the new helpers and cleanup behavior do not exist.

- [ ] **Step 3: Implement helpers and cleanup**

Replace `video-tagger/tagger/logic.py` with:

```python
import json
import re

MAX_TAG_LEN = 32
MAX_SINGLE_TOKEN_LEN = 24


class TagParseError(Exception):
    def __init__(self, raw_output: str):
        super().__init__("tag parser produced no usable tags")
        self.raw_output = raw_output


def _tags(bm):
    return {t.get("name") for t in bm.get("tags", [])}


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
    return re.sub(r"^```[a-zA-Z]*\n?|```$", "", text.strip()).strip()


def raw_tag_candidates(llm_text: str) -> list[str]:
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
    if (
        len(tag) > MAX_SINGLE_TOKEN_LEN
        and not re.search(r"[\s_-]", tag)
    ):
        return True
    return False


def parse_tags(llm_text: str) -> list[str]:
    seen = set()
    tags = []
    for raw in raw_tag_candidates(llm_text):
        tag = _normalize_tag(raw)
        if _is_bad_tag(tag):
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def _metadata_value(content: dict, key: str) -> str:
    value = content.get(key)
    if value is None:
        return ""
    return str(value).strip()


def has_tagging_signal(bm: dict, transcript: str) -> bool:
    if not is_empty_transcript(transcript or ""):
        return True
    content = bm.get("content", {}) or {}
    return any(_metadata_value(content, key) for key in ("title", "description", "text"))


def build_tagging_context(bm: dict, transcript: str) -> str:
    content = bm.get("content", {}) or {}
    sections = []
    transcript = (transcript or "").strip()
    if transcript:
        sections.append(("Transcript", transcript))
    for label, key in (
        ("Title", "title"),
        ("Description", "description"),
        ("Page Text", "text"),
        ("URL", "url"),
    ):
        value = _metadata_value(content, key)
        if value:
            sections.append((label, value))
    return "\n\n".join(f"{label}:\n{value}" for label, value in sections)


def is_empty_transcript(text: str) -> bool:
    t = re.sub(r"\[.*?\]", "", text, flags=re.I).strip()
    return len(t) < 3
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd video-tagger && pytest tests/test_logic.py -v
```

Expected: all logic tests pass.

- [ ] **Step 5: Commit**

```bash
git add video-tagger/tagger/logic.py video-tagger/tests/test_logic.py
git commit -m "feat(tagger): normalize tag output"
```

---

### Task 3: Make Ollama Tagging Content-Based and Retry Bad Parses

**Files:**
- Modify: `video-tagger/tagger/ollama.py`
- Test: `video-tagger/tests/test_ollama.py`

- [ ] **Step 1: Write failing tests for content prompt and parse errors**

Replace `video-tagger/tests/test_ollama.py` with:

```python
import json

import httpx
import pytest

from tagger.logic import TagParseError
from tagger.ollama import tags_from_content, tags_from_transcript


def test_tags_from_content_sends_metadata_context():
    def handler(req):
        assert req.url.path == "/api/chat"
        body = json.loads(req.read().decode())
        assert "format" not in body
        prompt = body["messages"][0]["content"]
        assert "Transcript:\nwe bake a cake" in prompt
        assert "Description:\nfamily recipe from grandma" in prompt
        return httpx.Response(200, json={"message": {"content": "Cooking, Recipe, Dessert"}})

    c = httpx.Client(transport=httpx.MockTransport(handler))

    assert tags_from_content(
        c,
        "http://o:11434",
        "llama3.2",
        "Transcript:\nwe bake a cake\n\nDescription:\nfamily recipe from grandma",
    ) == ["Cooking", "Recipe", "Dessert"]


def test_tags_from_transcript_keeps_compatibility():
    def handler(req):
        prompt = json.loads(req.read().decode())["messages"][0]["content"]
        assert "Transcript:\nwe bake a cake" in prompt
        return httpx.Response(200, json={"message": {"content": "Cooking, Recipe"}})

    c = httpx.Client(transport=httpx.MockTransport(handler))

    assert tags_from_transcript(c, "http://o:11434", "llama3.2", "we bake a cake") == [
        "Cooking",
        "Recipe",
    ]


def test_tags_from_content_raises_on_non_empty_unusable_output():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": "#fitnessexerciseweightlossmetabolismyogaenergybooststressrelief"
                }
            },
        )

    c = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(TagParseError) as err:
        tags_from_content(c, "http://o:11434", "llama3.2", "Transcript:\nfitness")

    assert "fitnessexercise" in err.value.raw_output
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd video-tagger && pytest tests/test_ollama.py -v
```

Expected: tests fail because `tags_from_content()` does not exist and bad parses do not raise.

- [ ] **Step 3: Implement content-based prompt and parse error**

Replace `video-tagger/tagger/ollama.py` with:

```python
import httpx

from tagger.logic import TagParseError, parse_tags, raw_tag_candidates

PROMPT = (
    "You are a tagging assistant. Read the video transcript and bookmark metadata. "
    "Reply with ONLY a comma-separated list of 5-12 concise topical tags. "
    "Do not include raw hashtags, concatenated hashtag blocks, very long tags, or commentary.\n\n"
    "{content}"
)


def tags_from_content(client: httpx.Client, base: str, model: str, content: str) -> list[str]:
    r = client.post(base.rstrip("/") + "/api/chat", timeout=300, json={
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": PROMPT.format(content=content[:6000])}],
    })
    r.raise_for_status()
    raw = r.json()["message"]["content"]
    tags = parse_tags(raw)
    if raw_tag_candidates(raw) and not tags:
        raise TagParseError(raw)
    return tags


def tags_from_transcript(client: httpx.Client, base: str, model: str, transcript: str) -> list[str]:
    return tags_from_content(client, base, model, f"Transcript:\n{transcript}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd video-tagger && pytest tests/test_ollama.py -v
```

Expected: all Ollama tests pass.

- [ ] **Step 5: Commit**

```bash
git add video-tagger/tagger/ollama.py video-tagger/tests/test_ollama.py
git commit -m "feat(tagger): tag from metadata context"
```

---

### Task 4: Integrate Metadata Context and Parse Failure Handling in Process

**Files:**
- Modify: `video-tagger/tagger/main.py`
- Test: `video-tagger/tests/test_main.py`

- [ ] **Step 1: Write failing tests for process behavior**

Update imports in `video-tagger/tests/test_main.py`:

```python
from tagger.logic import TagParseError
from tagger.main import DONE, process
```

Change `_bm_with_video()` to include content:

```python
def _bm_with_video(content=None):
    return {
        "id": "bm1",
        "tags": [],
        "content": content or {},
        "assets": [{"id": "asset1", "assetType": "video"}],
    }
```

Append these tests:

```python
def test_metadata_context_is_passed_to_tag_fn():
    kk = _make_kk()
    seen = {}

    def tag_fn(context):
        seen["context"] = context
        return ["Yoga", "Recovery"]

    process(
        _bm_with_video({
            "title": "Morning routine",
            "description": "Instagram caption about yoga and recovery",
            "url": "https://www.instagram.com/reel/abc/",
        }),
        kk,
        None,
        None,
        None,
        _transcribe_fn=lambda vid: "stretch your back",
        _tag_fn=tag_fn,
    )

    assert "Transcript:\nstretch your back" in seen["context"]
    assert "Description:\nInstagram caption about yoga and recovery" in seen["context"]
    kk.add_tags.assert_called_once_with("bm1", ["Yoga", "Recovery"])
    kk.add_tag.assert_called_once_with("bm1", DONE)


def test_no_speech_with_metadata_still_tags():
    kk = _make_kk()

    process(
        _bm_with_video({"description": "caption about pilates mobility"}),
        kk,
        None,
        None,
        None,
        _transcribe_fn=lambda vid: "",
        _tag_fn=lambda context: ["Pilates", "Mobility"],
    )

    kk.add_tags.assert_called_once_with("bm1", ["Pilates", "Mobility"])
    kk.add_tag.assert_called_once_with("bm1", DONE)


def test_no_speech_with_url_only_marks_done_without_tags():
    kk = _make_kk()

    process(
        _bm_with_video({"url": "https://www.instagram.com/reel/abc/"}),
        kk,
        None,
        None,
        None,
        _transcribe_fn=lambda vid: "",
        _tag_fn=lambda context: ["Instagram"],
    )

    kk.add_tags.assert_not_called()
    kk.add_tag.assert_called_once_with("bm1", DONE)


def test_parse_failure_does_not_mark_transcribed(caplog):
    kk = _make_kk()

    process(
        _bm_with_video(),
        kk,
        None,
        None,
        None,
        _transcribe_fn=lambda vid: "fitness tips",
        _tag_fn=lambda context: (_ for _ in ()).throw(
            TagParseError("#fitnessexerciseweightlossmetabolismyogaenergybooststressrelief")
        ),
    )

    kk.add_tags.assert_not_called()
    kk.add_tag.assert_not_called()
    assert "tag parse failed bm=bm1" in caplog.text
    assert "fitnessexercise" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd video-tagger && pytest tests/test_main.py -v
```

Expected: metadata/no-speech tests fail because `process()` still passes only transcript and marks empty transcript done.

- [ ] **Step 3: Implement process integration**

Replace `video-tagger/tagger/main.py` with:

```python
import logging
import os
import tempfile
import time

import httpx

from tagger.karakeep import KarakeepClient
from tagger.logic import TagParseError, build_tagging_context, has_tagging_signal, needs_tagging, video_asset_id
from tagger.ollama import tags_from_content
from tagger.transcribe import transcribe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("video-tagger")
DONE = "transcribed"


def _short(text: str, limit: int = 500) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def _note_text(transcript: str, context: str) -> str:
    return ("Transcript:\n" + (transcript or "").strip() + "\n\nTagging context:\n" + context)[:8000]


def process(bm, kk, oclient, obase, omodel, *, _transcribe_fn=None, _tag_fn=None):
    bid = bm["id"]
    aid = video_asset_id(bm)
    if not aid:
        return
    with tempfile.TemporaryDirectory() as d:
        vid = kk.get_asset_bytes(aid, f"{d}/v.mp4")
        try:
            if _transcribe_fn is not None:
                text = _transcribe_fn(vid)
            else:
                text = transcribe(vid, workdir=d)
        except Exception as e:
            log.error("transcribe failed %s: %s", bid, e)
            try:
                kk.add_tag(bid, DONE)
            except Exception as se:
                log.error("sentinel failed after transcribe error %s: %s", bid, se)
            return

        context = build_tagging_context(bm, text)
        if not has_tagging_signal(bm, text):
            log.info("no speech or useful metadata in %s; marking done", bid)
            try:
                kk.add_tag(bid, DONE)
            except Exception as se:
                log.error("sentinel failed for no-speech %s: %s", bid, se)
            return

        try:
            if _tag_fn is not None:
                tags = _tag_fn(context)
            else:
                tags = tags_from_content(oclient, obase, omodel, context)
        except TagParseError as e:
            log.error("tag parse failed bm=%s raw=%s", bid, _short(e.raw_output))
            return

        kk.add_tags(bid, tags)
        try:
            kk.set_note(bid, _note_text(text, context))
        except Exception as e:
            log.warning("set_note failed %s (non-fatal): %s", bid, e)
        try:
            kk.add_tag(bid, DONE)
        except Exception as e:
            log.error("sentinel failed %s: %s", bid, e)
        log.info("tagged %s with %d tags", bid, len(tags))


def main():
    kk = KarakeepClient(os.environ["KARAKEEP_API"], os.environ["KARAKEEP_TOKEN"])
    obase = os.environ.get("OLLAMA_API", "http://ollama:11434")
    omodel = os.environ.get("TAG_MODEL", "llama3.2")
    interval = int(os.environ.get("POLL_INTERVAL_SEC", "45"))
    oclient = httpx.Client()
    log.info("video-tagger up; polling every %ss", interval)
    while True:
        try:
            for bm in kk.list_recent():
                if needs_tagging(bm, DONE):
                    try:
                        process(bm, kk, oclient, obase, omodel)
                    except Exception as e:
                        log.error("process failed bm=%s: %s", bm.get("id"), e)
        except Exception as e:
            log.error("poll error: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd video-tagger && pytest tests/test_main.py -v
```

Expected: all main tests pass.

- [ ] **Step 5: Commit**

```bash
git add video-tagger/tagger/main.py video-tagger/tests/test_main.py
git commit -m "fix(tagger): retry invalid tag parses"
```

---

### Task 5: Update Runtime Configuration Docs

**Files:**
- Modify: `docker-compose.yml`
- Modify: `README.md`

- [ ] **Step 1: Update Docker Compose environment**

In `docker-compose.yml`, under the `video-tagger.environment` block after `WHISPER_MODEL`, add:

```yaml
      WHISPER_LANGUAGE: ${WHISPER_LANGUAGE:-auto}
```

- [ ] **Step 2: Update README behavior notes**

In `README.md`, update the setup/use notes so the relevant bullets read:

```markdown
- **Whisper** uses `small` (CPU/int8) by default — ~7× realtime on a modest box. Set
  `WHISPER_MODEL=base` (faster) or `medium` (more accurate) in `.env`. Set
  `WHISPER_LANGUAGE=ru` to force Russian transcription for short/noisy Russian reels;
  leave it unset or `auto` for Whisper language auto-detection.
- **Deep tagging uses transcript + bookmark metadata.** For Instagram reels, Karakeep
  page title/description text is included in the tagging prompt when available, so
  no-speech reels with useful captions can still receive topical tags.
- **Parse failures are retryable.** If the local model returns only unusable tags, such
  as a fused hashtag block, `video-tagger` logs `tag parse failed bm=<id> raw=<output>`
  and leaves the item unmarked so it can retry after prompt/model/config changes.
```

- [ ] **Step 3: Review docs diff**

Run:

```bash
git diff -- docker-compose.yml README.md
```

Expected: only `WHISPER_LANGUAGE` and behavior note updates appear.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml README.md
git commit -m "docs: document metadata tagging controls"
```

---

### Task 6: Run Full Verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Run video-tagger tests**

Run:

```bash
cd video-tagger && pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run video-fetcher tests**

Run:

```bash
cd video-fetcher && pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Check git status**

Run:

```bash
git status --short
```

Expected: clean working tree.

---

## Self-Review Notes

- Spec coverage: Tasks 1, 2, 3, 4, and 5 cover Russian transcription, Instagram/Karakeep metadata, parse observability, fused hashtag cleanup, notes, docs, and retry behavior.
- Scope: The plan does not change the downloader or fetch Instagram captions directly, matching the non-goals.
- Type consistency: `build_tagging_context()` returns the content string passed to `_tag_fn` and `tags_from_content()`. `TagParseError.raw_output` is the single path for logging raw bad model output.
