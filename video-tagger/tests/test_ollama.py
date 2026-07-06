import json

import httpx
import pytest

from tagger.logic import TagParseError
from tagger.ollama import tags_from_content, tags_from_transcript


def test_tags_from_content_sends_metadata_context():
    def handler(req):
        assert req.url.path == "/api/chat"
        body = json.loads(req.read().decode())
        assert "format" not in body
        prompt = body["messages"][0]["content"]
        assert "Transcript:\nwe bake a cake" in prompt
        assert "Description:\nfamily recipe from grandma" in prompt
        return httpx.Response(200, json={"message": {"content": "Cooking, Recipe, Dessert"}})

    c = httpx.Client(transport=httpx.MockTransport(handler))

    assert tags_from_content(
        c,
        "http://o:11434",
        "llama3.2",
        "Transcript:\nwe bake a cake\n\nDescription:\nfamily recipe from grandma",
    ) == ["Cooking", "Recipe", "Dessert"]


def test_tags_from_transcript_keeps_compatibility():
    def handler(req):
        prompt = json.loads(req.read().decode())["messages"][0]["content"]
        assert "Transcript:\nwe bake a cake" in prompt
        return httpx.Response(200, json={"message": {"content": "Cooking, Recipe"}})

    c = httpx.Client(transport=httpx.MockTransport(handler))

    assert tags_from_transcript(c, "http://o:11434", "llama3.2", "we bake a cake") == [
        "Cooking",
        "Recipe",
    ]


def test_tags_from_content_raises_on_non_empty_unusable_output():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": "#fitnessexerciseweightlossmetabolismyogaenergybooststressrelief"
                }
            },
        )

    c = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(TagParseError) as err:
        tags_from_content(c, "http://o:11434", "llama3.2", "Transcript:\nfitness")

    assert "fitnessexercise" in err.value.raw_output
