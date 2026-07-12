"""POST /search endpoint tests."""


def test_search_returns_top_k_results(client):
    response = client.post(
        "/search",
        json={"query": "入睡困难，多梦易醒，心悸健忘", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "入睡困难，多梦易醒，心悸健忘"
    assert body["top_k"] == 5
    assert len(body["results"]) == 5
    for item in body["results"]:
        assert "id" in item
        assert "name" in item
        assert "syndrome" in item
        assert 0.0 <= item["similarity_score"] <= 1.0


def test_search_rejects_empty_query(client):
    response = client.post("/search", json={"query": "", "top_k": 5})
    assert response.status_code == 422


def test_search_default_top_k(client):
    response = client.post("/search", json={"query": "心悸失眠"})
    assert response.status_code == 200
    assert response.json()["top_k"] == 5
