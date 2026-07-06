from tagger.transcribe import transcribe

class _Seg:
    def __init__(self, text): self.text = text

class _FakeModel:
    def transcribe(self, path, **kw):
        class _Info: language = "en"; duration = 1.0
        return [_Seg("hello "), _Seg("world")], _Info()

def test_transcribe_joins_segments(tmp_path):
    (tmp_path/"v.mp4").write_bytes(b"x")
    assert transcribe(str(tmp_path/"v.mp4"), model=_FakeModel()) == "hello world"


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
