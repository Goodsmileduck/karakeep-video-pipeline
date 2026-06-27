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
