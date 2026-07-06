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

def _bm(tags=(), assets=()):
    return {"id":"B","tags":[{"name":t} for t in tags],
            "assets":[{"id":f"a{i}","assetType":a} for i,a in enumerate(assets)]}

def test_needs_tagging():
    assert needs_tagging(_bm(assets=["video"]), "transcribed")
    assert not needs_tagging(_bm(assets=["video"], tags=["transcribed"]), "transcribed")
    assert not needs_tagging(_bm(assets=["image"]), "transcribed")  # no video

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
