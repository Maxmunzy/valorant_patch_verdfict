"""
main.py
FastAPI 서비스 — Valorant Patch Verdict

엔드포인트:
  GET /health          — 서버 상태
  GET /predict         — 전체 요원 예측 목록 (p_patch 내림차순)
  GET /predict/{agent} — 특정 요원 상세 예측 (설명 포함)
  POST /reload         — 데이터/모델 재로드
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import logging

from predict_service import PatchPredictor

logger = logging.getLogger("uvicorn.error")

predictor: PatchPredictor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    logger.info("모델 로드 중...")
    predictor = PatchPredictor()
    logger.info("모델 로드 완료")
    yield


app = FastAPI(
    title="Valorant Patch Verdict API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": predictor is not None}


@app.get("/predict")
def predict_all():
    """전체 요원 예측 — p_patch 내림차순."""
    if predictor is None:
        raise HTTPException(status_code=503, detail="모델 로드 중")
    return {"data": predictor.get_all()}


@app.get("/predict/{agent}")
def predict_agent(agent: str):
    """
    특정 요원 상세 예측.
    agent 이름은 영어 대소문자 무관 (e.g. neon, Neon, NEON 모두 가능).
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="모델 로드 중")

    # 이름 정규화: 첫 글자 대문자
    agent_normalized = agent.strip().title()

    # 특수 케이스 처리 (KAYO, KAY/O 둘 다 허용)
    AGENT_NAME_FIXES = {
        "Kay/O": "KAYO",
        "Kayo":  "KAYO",
    }
    agent_normalized = AGENT_NAME_FIXES.get(agent_normalized, agent_normalized)

    result = predictor.get_agent(agent_normalized)
    if result is None:
        raise HTTPException(status_code=404, detail=f"요원을 찾을 수 없습니다: {agent}")
    return result


@app.post("/reload")
def reload():
    """데이터/모델 재로드 (새 학습 후 적용)."""
    global predictor
    try:
        import importlib, predict_service as _ps
        importlib.reload(_ps)
        from predict_service import PatchPredictor as _PC
        predictor = _PC()
        return {"status": "ok", "message": "재로드 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
