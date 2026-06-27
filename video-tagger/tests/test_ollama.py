import httpx
from tagger.ollama import tags_from_transcript

def test_tags_from_transcript():
    def handler(req):
        assert req.url.path == "/api/chat"
        body = req.read().decode()
        import json; assert "format" not in json.loads(body)  # MUST NOT send a json schema/format on this box
        return httpx.Response(200, json={"message": {"content": "Cooking, Recipe, Dessert"}})
    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert tags_from_transcript(c, "http://o:11434", "llama3.2", "we bake a cake") == ["Cooking","Recipe","Dessert"]
