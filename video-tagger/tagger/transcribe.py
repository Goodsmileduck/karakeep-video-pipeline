import os

_model = None

def _default_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"),
                              device="cpu", compute_type="int8")
    return _model

def transcribe(video_path: str, *, model=None, workdir=None) -> str:  # workdir accepted but unused (reconciles Task-10 callsite)
    m = model or _default_model()
    segments, _info = m.transcribe(video_path)
    return " ".join(s.text.strip() for s in segments).strip()
