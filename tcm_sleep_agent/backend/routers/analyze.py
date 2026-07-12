"""POST /analyze — full RAG + Dynamic Few-shot pipeline endpoint."""

from fastapi import APIRouter, HTTPException

from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FewshotItem,
    FormulaItem,
)
from src.services.fewshot_service import build_fewshot_examples
from src.services.generation_service import generate_analysis
from src.services.retrieval_service import hybrid_search as retrieval_search

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Full pipeline: retrieval → dynamic few-shot → LLM generation."""
    try:
        retrieved = retrieval_search(req.query, top_k=req.top_k)
        fewshot = build_fewshot_examples(retrieved)
        analysis = generate_analysis(req.query, retrieved, fewshot)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    pipeline_steps = [
        "症状输入 → 文本预处理",
        "通义千问 text-embedding-v4 语义向量编码",
        f"BM25 稀疏检索 + Chroma 向量检索 → RRF 融合 Top {req.top_k}",
        f"动态 Few-shot 构建 → MMR 多样性选取 {len(fewshot)} 条参考医案",
        "DeepSeek 基于参考医案 + 检索知识生成结构化处方分析",
    ]

    return AnalyzeResponse(
        query=req.query,
        retrieved=[FormulaItem(**item) for item in retrieved],
        fewshot=[FewshotItem(**item) for item in fewshot],
        analysis=analysis,
        pipeline_steps=pipeline_steps,
    )
