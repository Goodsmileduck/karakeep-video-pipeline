# Video Tagger Metadata, Russian Transcription, and Parsing Design

## Context

The current pipeline downloads videos in `video-fetcher` and tags them in
`video-tagger`. Tagging is audio-only today: `tagger.main.process()` transcribes the
video and passes only the transcript to `tagger.ollama.tags_from_transcript()`.

That explains the reported behavior:

- Instagram reel descriptions are ignored because bookmark metadata is never included
  in the LLM prompt.
- Russian recognition relies entirely on Whisper auto-detection, with no language
  override and no logging of detected language.
- Parsing failures are hard to diagnose because raw LLM output is not logged when tag
  parsing fails or produces unusable tags.
- Long fused hashtags pass through because tag parsing does not normalize or filter
  output.

No local Docker containers were running during investigation, so live logs were not
available. The implementation should improve future observability instead of relying
on ad hoc log inspection.

## Goals

- Use available Karakeep bookmark metadata, including Instagram descriptions, as part
  of tag generation.
- Allow Russian transcription to be forced with configuration while keeping automatic
  language detection as the default.
- Make parse/tagging failures visible with bookmark id and shortened raw model output.
- Prevent low-quality long hashtag tags from being written to Karakeep.
- Preserve current idempotency behavior: successful items receive `transcribed`;
  retryable tagging failures should not be marked done.

## Non-Goals

- Fetch Instagram captions directly from Instagram or yt-dlp metadata.
- Change Cobalt or yt-dlp downloader behavior.
- Add a new database or persistent error store.
- Switch LLM providers or require structured Ollama output, since existing tests note
  this environment must not send Ollama JSON schema/format options.

## Proposed Approach

### Tagging Input

Add a small helper in `video-tagger` that builds a tagging context from:

- transcript text,
- bookmark title,
- bookmark description,
- bookmark text/content fields where present,
- bookmark URL.

The helper should be defensive about Karakeep response shape and ignore missing fields.
It should label sections clearly so the model can distinguish spoken transcript from
page metadata.

The LLM prompt should become content-based rather than transcript-only. It should ask
for 5-12 concise topical tags and explicitly reject raw hashtags, concatenated hashtag
blocks, commentary, and very long tags.

### Transcription Language

Add `WHISPER_LANGUAGE` to `video-tagger` configuration:

- default: unset or `auto`, preserving current auto-detection,
- `ru`: pass `language="ru"` to faster-whisper,
- any other non-empty value: pass that language code through.

`transcribe()` should log detected language and probability when faster-whisper returns
that metadata. Tests should use a fake model to verify options are passed correctly.

### Tag Parsing and Cleanup

Keep supporting the current parser inputs:

- JSON arrays,
- comma-separated text,
- newline-separated text,
- fenced code blocks.

Then normalize parsed candidates:

- strip whitespace,
- remove leading `#`,
- collapse internal whitespace,
- deduplicate case-insensitively while preserving order,
- reject empty tags,
- reject tags longer than a configurable internal limit, initially 32 characters,
- reject single-token hashtag-like values longer than 24 characters when they contain
  no spaces, hyphens, or underscores. This catches fused blocks like
  `fitnessexerciseweightlossmetabolism...` without trying to split them.

The parser should return a clean list. If the model response is non-empty but cleaning
removes every candidate, treat that as a parse failure at the process layer so the item
can be retried after prompt/model changes.

### Error Handling and Logging

Introduce a specific parse/tagging failure path in `process()`:

- log bookmark id,
- log a shortened raw model response,
- leave the bookmark without `transcribed` so it can retry,
- do not write empty or invalid tags.

Keep no-speech behavior unchanged: if transcript and metadata context are empty enough
to be useless, mark done without tags. If metadata exists even when speech is empty,
still attempt metadata-based tagging.

### Notes

When note writing succeeds, include both transcript and the metadata context used for
tagging, bounded to the current note size limit. This makes later debugging possible
from the Karakeep item itself.

## Testing Plan

Write failing tests before production changes:

- metadata context includes Instagram-like description fields and is passed to the tag
  function,
- no-speech with useful metadata still tags instead of immediately marking done,
- `WHISPER_LANGUAGE=ru` results in `language="ru"` passed to the model,
- auto language omits the language option,
- long fused hashtags are filtered,
- valid JSON and comma/newline outputs still parse,
- a non-empty LLM response that cleans to no usable tags logs a parse failure and does
  not add the `transcribed` sentinel.

After implementation, run the existing unit test suite for both services.
