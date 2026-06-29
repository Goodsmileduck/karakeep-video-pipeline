from unittest.mock import MagicMock, call
from tagger.main import process, DONE, FAILED


def _raise(_vid):
    raise RuntimeError("tuple index out of range")


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


def test_transcribe_error_marks_failed_not_done():
    """A non-video asset crashes whisper → tag FAILED (not the DONE success sentinel).

    Previously the except block wrote DONE, masking the failure as success so it
    looked tagged with zero content tags and was never retried.
    """
    kk = _make_kk()
    process(
        _bm_with_video(), kk, None, None, None,
        _transcribe_fn=_raise,
        _tag_fn=lambda text: ["should", "not", "run"],
    )
    kk.add_tag.assert_called_once_with("bm1", FAILED)
    kk.add_tags.assert_not_called()


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
