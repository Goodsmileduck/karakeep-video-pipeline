from tagger.logic import needs_tagging, video_asset_id, parse_tags, is_empty_transcript

def _bm(tags=(), assets=()):
    return {"id":"B","tags":[{"name":t} for t in tags],
            "assets":[{"id":f"a{i}","assetType":a} for i,a in enumerate(assets)]}

def test_needs_tagging():
    assert needs_tagging(_bm(assets=["video"]), "transcribed")
    assert not needs_tagging(_bm(assets=["video"], tags=["transcribed"]), "transcribed")
    assert not needs_tagging(_bm(assets=["image"]), "transcribed")  # no video

def test_needs_tagging_skips_failed():
    # a bookmark already marked transcribe-failed must not be retried forever
    assert not needs_tagging(
        _bm(assets=["video"], tags=["transcribe-failed"]), "transcribed", "transcribe-failed")
    # still picks up a fresh video when neither sentinel is present
    assert needs_tagging(_bm(assets=["video"]), "transcribed", "transcribe-failed")

def test_video_asset_id():
    assert video_asset_id(_bm(assets=["image","video"])) == "a1"
    assert video_asset_id(_bm(assets=["image"])) is None

def test_parse_tags():
    assert parse_tags("```json\n[\"Cooking\",\"Recipe\"]\n```") == ["Cooking","Recipe"]
    assert parse_tags("Cooking, Recipe, Dessert") == ["Cooking","Recipe","Dessert"]
    assert parse_tags("") == []

def test_is_empty_transcript():
    assert is_empty_transcript("   ")
    assert is_empty_transcript("[music]")
    assert is_empty_transcript("[BLANK_AUDIO]")
    assert not is_empty_transcript("hello there everyone")
