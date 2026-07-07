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
