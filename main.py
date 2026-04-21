"""
FastAPI application for the Valorant Patch Verdict API.

Endpoints:
  GET  /health
  GET  /predict
  GET  /predict/{agent}
  POST /simulate
  POST /simulate-analyze
  GET  /agent-skills
  POST /reload
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_data import normalize_agent
from explanation_service import generate_sim_analysis
from patch_simulator import PatchSimulator, StatChange
from predict_service import PatchPredictor

logger = logging.getLogger("uvicorn.error")

BASE_DIR = Path(__file__).resolve().parent
REQUIRED_FILES = (
    BASE_DIR / "step2_pipeline.pkl",
    BASE_DIR / "step2_training_data.csv",
    BASE_DIR / "data" / "agent_skills.json",
)

predictor: PatchPredictor | None = None
simulator: PatchSimulator | None = None


def missing_runtime_files() -> list[str]:
    return [str(path.relative_to(BASE_DIR)) for path in REQUIRED_FILES if not path.exists()]


def ensure_services_ready() -> None:
    if predictor is None or simulator is None:
        missing = missing_runtime_files()
        detail = "Model services are not loaded."
        if missing:
            detail += f" Missing runtime files: {', '.join(missing)}"
        raise HTTPException(status_code=503, detail=detail)


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    global predictor, simulator

    missing = missing_runtime_files()
    if missing:
        logger.error("Startup skipped because runtime files are missing: %s", ", ".join(missing))
        predictor = None
        simulator = None
        yield
        return

    logger.info("Loading predictor and simulator")
    predictor = PatchPredictor()
    simulator = PatchSimulator()
    logger.info("Predictor and simulator are ready")
    yield


app = FastAPI(
    title="Valorant Patch Verdict API",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://whosnxt.app",
        "https://www.whosnxt.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatChangeRequest(BaseModel):
    agent: str
    skill: str
    stat: str
    old_value: float
    new_value: float


class SimulateRequest(BaseModel):
    changes: list[StatChangeRequest]


class SimAnalyzeRequest(BaseModel):
    changes: list[StatChangeRequest]
    result_summary: str


@app.get("/health")
def health():
    missing = missing_runtime_files()
    return {
        "status": "ok" if not missing else "degraded",
        "model_loaded": predictor is not None,
        "simulator_loaded": simulator is not None,
        "anthropic_key_present": bool(os.getenv("ANTHROPIC_API_KEY")),
        "missing_runtime_files": missing,
    }


@app.get("/predict")
def predict_all():
    ensure_services_ready()
    return {"data": predictor.get_all()}


@app.get("/predict/{agent}")
def predict_agent(agent: str):
    ensure_services_ready()
    agent_normalized = normalize_agent(agent)
    result = predictor.get_agent(agent_normalized)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent}")
    return result


@app.post("/simulate")
def simulate(req: SimulateRequest):
    ensure_services_ready()
    if not req.changes:
        raise HTTPException(status_code=400, detail="At least one change is required.")

    changes: list[StatChange] = []
    for change in req.changes:
        skill = change.skill.upper()
        if skill not in {"Q", "E", "C", "X"}:
            raise HTTPException(status_code=400, detail=f"Invalid skill slot: {change.skill}")

        changes.append(
            StatChange(
                agent=normalize_agent(change.agent),
                skill=skill,
                stat_name=change.stat,
                old_value=change.old_value,
                new_value=change.new_value,
            )
        )

    try:
        result = simulator.simulate(changes)
        return result.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/simulate-analyze")
def simulate_analyze(req: SimAnalyzeRequest):
    changes_desc = "\n".join(
        f"- {change.agent} [{change.skill.upper()}] {change.stat}: {change.old_value} -> {change.new_value}"
        for change in req.changes
    )

    target_agents: list[str] = []
    seen: set[str] = set()
    for change in req.changes:
        normalized = normalize_agent(change.agent)
        if normalized not in seen:
            seen.add(normalized)
            target_agents.append(normalized)

    analysis = generate_sim_analysis(
        changes_desc,
        req.result_summary,
        target_agents=target_agents,
    )
    return {"analysis": analysis}


@app.get("/agent-skills")
def agent_skills():
    from agent_data import AGENT_KIT, AGENT_ROLE_KO

    path = BASE_DIR / "data" / "agent_skills.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="agent_skills.json not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    for agent, slots in data.items():
        kit = AGENT_KIT.get(agent, {})
        role = AGENT_ROLE_KO.get(agent, "")
        for slot_key, slot_data in slots.items():
            if slot_key in kit and "ko" in kit[slot_key]:
                slot_data["name_ko"] = kit[slot_key]["ko"]
        slots["_meta"] = {"role_ko": role}
    return data


@app.post("/reload")
def reload():
    global predictor, simulator

    missing = missing_runtime_files()
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reload while runtime files are missing: {', '.join(missing)}",
        )

    try:
        import importlib
        import patch_simulator as simulator_module
        import predict_service as predictor_module

        importlib.reload(predictor_module)
        importlib.reload(simulator_module)
        predictor = predictor_module.PatchPredictor()
        simulator = simulator_module.PatchSimulator()
        return {"status": "ok", "message": "Predictor and simulator reloaded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
