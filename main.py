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
import logging

from predict_service import PatchPredictor
from patch_simulator import PatchSimulator, StatChange
from agent_data import normalize_agent
from explanation_service import generate_sim_analysis

logger = logging.getLogger("uvicorn.error")

predictor: PatchPredictor | None = None
simulator: PatchSimulator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor, simulator
    logger.info("모델 로드 중...")
    predictor = PatchPredictor()
    simulator = PatchSimulator()
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

    agent_normalized = normalize_agent(agent)

    result = predictor.get_agent(agent_normalized)
    if result is None:
        raise HTTPException(status_code=404, detail=f"요원을 찾을 수 없습니다: {agent}")
    return result


# ─── 패치 시뮬레이터 ────────────────────────────────────────────────────────

class StatChangeRequest(BaseModel):
    agent: str           # 요원 이름 (한/영, 대소문자 무관)
    skill: str           # "Q" | "E" | "C" | "X"
    stat: str            # 변경 스탯 (e.g. "cooldown", "damage")
    old_value: float     # 현재 값
    new_value: float     # 변경 후 값

class SimulateRequest(BaseModel):
    changes: list[StatChangeRequest]




@app.post("/simulate")
def simulate(req: SimulateRequest):
    """
    가상 패치 시뮬레이션.
    변경사항을 입력하면 전 요원의 before/after 예측을 반환.

    예시 요청:
    {
      "changes": [
        {"agent": "Neon", "skill": "E", "stat": "cooldown", "old_value": 6, "new_value": 8}
      ]
    }
    """
    if simulator is None:
        raise HTTPException(status_code=503, detail="시뮬레이터 로드 중")

    if not req.changes:
        raise HTTPException(status_code=400, detail="변경사항이 비어있습니다")

    changes = []
    for c in req.changes:
        agent = normalize_agent(c.agent)
        if c.skill.upper() not in ("Q", "E", "C", "X"):
            raise HTTPException(status_code=400, detail=f"잘못된 스킬 슬롯: {c.skill}")
        changes.append(StatChange(
            agent=agent,
            skill=c.skill.upper(),
            stat_name=c.stat,
            old_value=c.old_value,
            new_value=c.new_value,
        ))

    try:
        result = simulator.simulate(changes)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SimAnalyzeRequest(BaseModel):
    changes: list[StatChangeRequest]
    result_summary: str  # 프론트에서 정리한 결과 요약


@app.post("/simulate-analyze")
def simulate_analyze(req: SimAnalyzeRequest):
    """시뮬레이션 결과에 대한 AI 분석을 생성한다."""
    changes_desc = "\n".join(
        f"- {c.agent} [{c.skill}] {c.stat}: {c.old_value} → {c.new_value}"
        for c in req.changes
    )
    analysis = generate_sim_analysis(changes_desc, req.result_summary)
    return {"analysis": analysis}


@app.get("/agent-skills")
def agent_skills():
    """전 요원 스킬 데이터 (시뮬레이터 UI용). 한국어 스킬명 + 역할 포함."""
    import json
    from pathlib import Path
    from agent_data import AGENT_KIT, AGENT_ROLE_KO
    path = Path(__file__).parent / "data" / "agent_skills.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="agent_skills.json not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    # 한국어 스킬명 + 역할 주입
    for agent, slots in data.items():
        kit = AGENT_KIT.get(agent, {})
        role = AGENT_ROLE_KO.get(agent, "")
        for slot_key, slot_data in slots.items():
            if slot_key in kit and "ko" in kit[slot_key]:
                slot_data["name_ko"] = kit[slot_key]["ko"]
        # 에이전트 레벨 메타 (첫 슬롯에 _meta로 추가하면 구조 깨짐 → 별도 키)
        slots["_meta"] = {"role_ko": role}
    return data


@app.post("/reload")
def reload():
    """데이터/모델 재로드 (새 학습 후 적용). predictor + simulator 모두 재생성."""
    global predictor, simulator
    try:
        import importlib
        import predict_service as _ps, patch_simulator as _sim
        importlib.reload(_ps)
        importlib.reload(_sim)
        from predict_service import PatchPredictor as _PC
        from patch_simulator import PatchSimulator as _PS
        predictor = _PC()
        simulator = _PS()
        return {"status": "ok", "message": "predictor + simulator 재로드 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn, socket

    # 기존 프로세스가 포트를 점유 중이면 강제 종료
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sock.connect_ex(("127.0.0.1", 8000)) == 0:
        sock.close()
        import subprocess
        subprocess.run(
            ["powershell", "-Command",
             "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
             "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"],
            capture_output=True,
        )
        import time; time.sleep(0.5)
    else:
        sock.close()

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
