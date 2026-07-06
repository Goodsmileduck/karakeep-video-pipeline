from unittest.mock import MagicMock, call
from tagger.logic import TagParseError
from tagger.main import DONE, process


def _bm_with_video(content=None):
    return {
        "id": "bm1",
        "tags": [],
        "content": content or {},
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
