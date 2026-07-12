"""GET /knowledge/* endpoint tests."""


def test_knowledge_count(client):
    response = client.get("/knowledge/count")
    assert response.status_code == 200
    body = response.json()
    assert body["sqlite_count"] >= 20
    assert body["chroma_count"] >= 20


def test_knowledge_get_by_id_returns_formula(client):
    list_resp = client.get("/knowledge/list")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    first_id = items[0]["id"]

    detail_resp = client.get(f"/knowledge/{first_id}")
    assert detail_resp.status_code == 200
    body = detail_resp.json()
    assert body["id"] == first_id
    assert "name" in body
    assert "example_case" in body


def test_knowledge_get_unknown_returns_404(client):
    response = client.get("/knowledge/__nonexistent__")
    assert response.status_code == 404
