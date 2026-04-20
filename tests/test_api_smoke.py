"""
test_api_smoke.py
FastAPI 엔드포인트 스모크 테스트

검증 대상:
  GET  /health          — 서버 상태
  GET  /predict         — 전체 요원 예측
  GET  /predict/{agent} — 단일 요원 상세 (+ 404 처리)
  POST /simulate        — 패치 시뮬레이션 (+ 빈 입력 400)
  POST /reload          — 모델 재로드
  GET  /agent-skills    — 스킬 데이터 (시뮬레이터 UI용)

실행:
  pytest tests/test_api_smoke.py -v
"""

import pytest
from fastapi.testclient import TestClient

from main import app


# ─── fixture: lifespan 내에서 predictor/simulator 로드 ─────────────────────

@pytest.fixture(scope="module")
def client():
    """TestClient를 context manager로 열어 lifespan(모델 로드)을 실행."""
    with TestClient(app) as c:
        yield c


# ─── /health ───────────────────────────────────────────────────────────────

def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


# ─── /predict (전체) ───────────────────────────────────────────────────────

def test_predict_all(client: TestClient):
    r = client.get("/predict")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 25  # 현재 29요원

    first = data[0]
    # 필수 필드 존재 확인
    required = {
        "agent", "role", "p_patch", "p_buff", "p_nerf",
        "verdict", "verdict_ko", "urgency_score", "signals",
    }
    assert required.issubset(first.keys()), f"missing: {required - first.keys()}"

    # p_patch 값 범위 확인
    for d in data:
        assert 0 <= d["p_patch"] <= 100, f"{d['agent']} p_patch={d['p_patch']} 범위 초과"


# ─── /predict/{agent} (단일 요원) ──────────────────────────────────────────

def test_predict_single_agent(client: TestClient):
    """대소문자 무관 조회 + 필수 필드."""
    for name in ("neon", "Neon", "NEON"):
        r = client.get(f"/predict/{name}")
        assert r.status_code == 200, f"{name} → {r.status_code}"
        body = r.json()
        assert body["agent"] == "Neon"
        assert 0 <= body["p_nerf"] <= 100
        assert 0 <= body["p_buff"] <= 100


def test_predict_unknown_agent_404(client: TestClient):
    r = client.get("/predict/UnknownAgent999")
    assert r.status_code == 404


# ─── /simulate ─────────────────────────────────────────────────────────────

def test_simulate_basic(client: TestClient):
    """단일 변경 시뮬레이션 — 응답 구조 검증."""
    payload = {
        "changes": [
            {
                "agent": "Neon",
                "skill": "E",
                "stat": "cooldown",
                "old_value": 6,
                "new_value": 8,
            }
        ]
    }
    r = client.post("/simulate", json=payload)
    assert r.status_code == 200

    body = r.json()
    # 필수 최상위 키
    for key in ("changes", "impact", "before_ranking", "after_ranking"):
        assert key in body, f"missing key: {key}"

    # impact에 변경 요원 포함
    impact_agents = [i["agent"] for i in body["impact"]]
    assert "Neon" in impact_agents

    # Phase 2 신규 필드: 범위, 신뢰도, 유사 사례
    neon_imp = next(i for i in body["impact"] if i["agent"] == "Neon")
    assert neon_imp["confidence"] in ("high", "medium", "low")
    assert len(neon_imp["pr_range"]) == 3  # [p25, median, p75]
    assert len(neon_imp["wr_range"]) == 3
    assert neon_imp["n_samples"] > 0
    assert isinstance(neon_imp["similar_cases"], list)

    # ranking은 전 요원 포함
    assert len(body["before_ranking"]) >= 25
    assert len(body["after_ranking"]) >= 25


def test_simulate_empty_changes_400(client: TestClient):
    r = client.post("/simulate", json={"changes": []})
    assert r.status_code == 400


def test_simulate_invalid_skill_400(client: TestClient):
    payload = {
        "changes": [
            {
                "agent": "Neon",
                "skill": "Z",  # 잘못된 슬롯
                "stat": "cooldown",
                "old_value": 6,
                "new_value": 8,
            }
        ]
    }
    r = client.post("/simulate", json=payload)
    assert r.status_code == 400


# ─── /agent-skills ─────────────────────────────────────────────────────────

def test_agent_skills(client: TestClient):
    r = client.get("/agent-skills")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert len(data) >= 25

    # 아무 요원이나 하나 검증: _meta.role_ko 존재, 슬롯에 name_ko 존재
    neon = data.get("Neon", {})
    assert "_meta" in neon
    assert "role_ko" in neon["_meta"]

    # 스킬 슬롯 중 하나에 name_ko가 있는지
    has_ko = any(
        "name_ko" in slot_data
        for key, slot_data in neon.items()
        if key != "_meta" and isinstance(slot_data, dict)
    )
    assert has_ko, "Neon 스킬에 name_ko가 없음"


# ─── /reload ───────────────────────────────────────────────────────────────

def test_reload(client: TestClient):
    """reload 후에도 predict가 정상 동작하는지 검증."""
    r = client.post("/reload")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"

    # reload 후 predict 정상 확인
    r2 = client.get("/predict")
    assert r2.status_code == 200
    assert len(r2.json()["data"]) >= 25
