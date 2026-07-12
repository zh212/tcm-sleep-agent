"""POST /analyze endpoint tests."""

import os

import pytest


REQUIRES_LLM = pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not configured",
)


@REQUIRES_LLM
def test_analyze_full_pipeline(client):
    response = client.post(
        "/analyze",
        json={"query": "入睡困难，多梦易醒，心悸健忘", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "入睡困难，多梦易醒，心悸健忘"
    assert len(body["retrieved"]) == 5
    assert isinstance(body["fewshot"], list)
    assert isinstance(body["analysis"], str)
    assert len(body["analysis"]) > 0
    assert isinstance(body["pipeline_steps"], list)
    assert len(body["pipeline_steps"]) >= 3


def test_analyze_rejects_empty_query(client):
    response = client.post("/analyze", json={"query": "", "top_k": 5})
    assert response.status_code == 422
