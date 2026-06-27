from unittest.mock import MagicMock, call
from tagger.main import process, DONE


def _bm_with_video():
    return {
        "id": "bm1",
        "tags": [],
        "assets": [{"id": "asset1", "assetType": "video"}],
    }


def _make_kk():
    kk = MagicMock()
    kk.get_asset_bytes.return_value = "/fake/v.mp4"
    return kk


def test_no_speech_marks_done_no_add_tags():
    """transcribe returns empty → add_tag(DONE) called; add_tags NOT called."""
    kk = _make_kk()
    process(
        _bm_with_video(), kk, None, None, None,
        _transcribe_fn=lambda vid: "",
        _tag_fn=lambda text: [],
    )
    kk.add_tag.assert_called_once_with("bm1", DONE)
    kk.add_tags.assert_not_called()


def test_tags_and_sentinel():
    """transcribe returns text, tagging returns tags → add_tags + add_tag(DONE)."""
    kk = _make_kk()
    process(
        _bm_with_video(), kk, None, None, None,
        _transcribe_fn=lambda vid: "we bake a cake",
        _tag_fn=lambda text: ["Cooking", "Recipe"],
    )
    kk.add_tags.assert_called_once_with("bm1", ["Cooking", "Recipe"])
    kk.add_tag.assert_called_once_with("bm1", DONE)


def test_note_failure_still_sentinels():
    """set_note raises → add_tag(DONE) is still called (sentinel is not lost)."""
    kk = _make_kk()
    kk.set_note.side_effect = Exception("network error")
    process(
        _bm_with_video(), kk, None, None, None,
        _transcribe_fn=lambda vid: "we bake a cake",
        _tag_fn=lambda text: ["Cooking", "Recipe"],
    )
    kk.add_tags.assert_called_once_with("bm1", ["Cooking", "Recipe"])
    kk.add_tag.assert_called_once_with("bm1", DONE)
