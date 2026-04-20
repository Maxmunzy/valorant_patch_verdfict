# Valorant Patch Verdict

[한국어 README](README_KR.md)

**Live Demo**: [whosnxt.app](https://whosnxt.app) · API: [api.whosnxt.app](https://api.whosnxt.app/health)

## Overview

> **Predict who gets patched next, and simulate how any patch changes the meta.**

A machine learning system that predicts Valorant agent patch pressure using ranked pick/win rates, VCT tournament data, patch history, and agent design characteristics.

Given current meta data, the model outputs nerf/buff/stable probabilities for all 29 agents.

---

## How It Works

### 2-Stage Hierarchical Classification

```
Input: Agent + Act features (ranked stats, VCT stats, patch history, design traits)
                    |
           [Stage A: XGBoost]  (50 features)
           stable vs patched?
                /         \
          stable        patched
                          |
                   [Stage B: XGBoost]  (51 features)
                   buff vs nerf?
                    /         \
                 buff         nerf
                    |           |
              mild / strong  mild / strong
```

**Stage A** determines whether an agent is under patch pressure.
**Stage B** determines the direction (buff or nerf).
Each stage uses its own optimized feature set.
Severity (mild/strong) comes from patch context and skill importance.

### Current Performance (2026-04-16)

| Metric | Value |
|---|---|
| Stage A balanced accuracy | 0.6614 |
| Stage B balanced accuracy | 0.7779 |
| Training data | 659 rows / 29 agents / E2A1 ~ V26A2 |
| Stage A features | 50 |
| Stage B features | 51 |

---

## Latest Predictions (V26A2 / Patch 12.07, retrained 2026-04-17)

### Nerf Ranking

| # | Agent | p_nerf | Rank PR | VCT PR |
|---|---|---|---|---|
| 1 | Neon | 77.1% | 22.3% | 43.8% |
| 2 | Waylay | 75.2% | 36.3% | 44.2% |
| 3 | Omen | 72.0% | 16.9% | 48.1% |
| 4 | Viper | 60.4% | 6.4% | 55.4% |
| 5 | Sova | 48.6% | 32.4% | 40.5% |

### Buff Ranking

| # | Agent | p_buff | Rank PR | VCT PR |
|---|---|---|---|---|
| 1 | KAYO | 79.7% | 4.6% | 8.5% |
| 2 | Gekko | 66.6% | 4.9% | 2.0% |
| 3 | Yoru | 63.6% | 3.1% | 1.8% |
| 4 | Breach | 53.5% | 8.0% | 6.2% |
| 5 | Vyse | 51.5% | 5.1% | 5.6% |

---

## Data Sources

| Source | Data | Period |
|---|---|---|
| vstats.gg | Per-act pick rate, win rate, match count (Diamond+, all regions) | E6A3~ |
| maxmunzy/valorant-agent-stats | Diamond+ pick rate, win rate, KD | E2A1~E9A3 |
| vlr.gg | VCT tournament pick rate, win rate | E6A3~ |
| playvalorant.com | Official patch notes | E2A1~ |

- **Tier**: Diamond+ (lower ranks are preference-driven, too noisy)
- **Region**: All regions combined (Valorant patches globally, small agent pool limits regional variance)
- **Merge**: vstats.gg primary, maxmunzy fills E2A1~E6A2 gap

---

## Model Architecture

### Feature Engineering: 2D Quadrant System

The core insight: Riot's patch decisions operate on a **2D plane (pick rate x win rate)**, not 1D metrics independently. Features are designed around this:

**Rank 2D Quadrants** (centered on agent's own historical baseline):
```
                   WR above agent avg
                        |
    Q2 Niche OP         |         Q1 Nerf target
    (low PR, high WR)   |   (high PR, high WR)
                         |
   ──────────────────────┼──────────────── PR above baseline
                         |
    Q3 Buff target       |         Q4 Fandom
    (low PR, low WR)     |   (high PR, low WR)
                         |
                   WR below agent avg
```

**VCT Features**:
- `vct_must_nerf`: absolute dominance threshold (VCT PR > 35%)
- `pro_only_nerf`: VCT dominant + rank not popular (Viper/Omen type)

**Stage-Specific Features**:
- Stage A gets `map_hhi`, `kit_score`, `recent_dual_miss_count`, `vct_pr_avg`
- Stage B gets `vct_data_lag`, `geo_synergy`, `n_nerf_patches`, `n_total_patches`, `vct_pr_peak_all`

### Labeling System

5-class labels with two key innovations:

**1. VCT Absolute Threshold**
Agents with VCT pick rate > 35% receive `mild_nerf` label regardless of their historical average.
This catches agents like Viper (always high VCT) that relative metrics miss.

**2. Signal Carryover**
If an agent was labeled `mild_nerf` in act N, the signal persists into act N+1 unless metrics normalize.
This prevents flickering between stable/nerf for agents under sustained pressure.

| Label | Description |
|---|---|
| `stable` | Metrics near baseline, no patch pressure |
| `mild_nerf` | Nerf signal present (rank excess or VCT dominance) |
| `strong_nerf` | Actual patch: followup/correction or core skill (E/X) nerf |
| `mild_buff` | Buff signal present (below baseline + losing) |
| `strong_buff` | Actual patch: followup/correction, core skill buff, or rework |

### Training Pipeline

- **Stage A**: Walk-forward temporal CV, train-only 1:1 undersampling (stable majority reduced to match patched count)
- **Stage B**: Walk-forward temporal CV, SMOTE oversampling (buff minority)
- **HPO**: Optuna TPE Sampler (60 trials per stage)
- **Feature selection**: Stage A/B each have independent feature sets optimized by SHAP importance
- **No domain rules**: Model output used directly without post-hoc probability adjustments

### Top SHAP Features

**Stage A (stable vs patched) — 50 features:**

| Rank | Feature | SHAP |
|---|---|---|
| 1 | rank_pr_excess | 0.163 |
| 2 | vct_pr_last | 0.155 |
| 3 | wr_buff_signal | 0.133 |
| 4 | strength_vs_direction | 0.123 |
| 5 | tier_gap | 0.122 |
| 6 | rank_pr_slope | 0.119 |
| 7 | last_pr_pre | 0.103 |
| 8 | rank_wr | 0.098 |
| 9 | kit_x_rank_pr | 0.089 |
| 10 | kit_score | 0.080 |

**Stage B (buff vs nerf) — 51 features:**

| Rank | Feature | SHAP |
|---|---|---|
| 1 | rank_pr_avg3 | 0.383 |
| 2 | pr_pct_of_peak | 0.346 |
| 3 | skill_ceiling_x_vct_pr | 0.342 |
| 4 | vct_pr_last | 0.291 |
| 5 | last_pr_pre | 0.280 |
| 6 | vct_wr_last | 0.280 |
| 7 | rank_pr | 0.277 |
| 8 | acts_since_patch | 0.251 |
| 9 | vct_rel_pos | 0.236 |
| 10 | rank_pr_vs_peak | 0.212 |

---

## Project Structure

```
valorant_patch_verdict/
  main.py                  # FastAPI server
  predict_service.py       # Prediction API wrapper
  explanation_service.py   # AI analysis (Claude Haiku, role-aware prompts)
  patch_simulator.py       # Patch simulator (virtual patch -> meta delta)
  auto_update.py           # Auto-update pipeline (detect -> crawl -> reload)
  build_step2_data.py      # Training data builder
  label_builder.py         # 5-class labeling logic
  feature_builder.py       # Feature engineering (2D quadrants, signals)
  train_step2.py           # Model training pipeline (HPO, CV, SHAP)
  agent_data.py            # Agent design data, skill weights, skill ceiling
  crawl_patch_notes.py     # Patch note crawler
  crawl_current_vct.py     # VCT tournament data crawler
  crawl_tracker.py         # Ranked stats crawler (vstats.gg)
  data/                    # Raw data + per-agent patch history
  frontend/                # Next.js + Tailwind CSS frontend (simulator included)
  step2_training_data.csv  # Built training data
  step2_pipeline.pkl       # Trained model artifact
```

---

## Run

Backend (FastAPI) and frontend (Next.js) run as separate processes.

```bash
# ── Backend ────────────────────────────────
# Build training data
python build_step2_data.py

# Train model (full HPO)
python train_step2.py

# Fast mode (reuse saved hyperparams)
python train_step2.py --fast

# Start API server (port 8000)
python main.py

# Auto-update: detect new patch -> crawl -> refresh predictions
python auto_update.py
```

```bash
# ── Frontend ───────────────────────────────
cd frontend
npm install
npm run dev        # dev server (port 3000)
npm run build      # production build
```

Required env vars:
- Backend: `ANTHROPIC_API_KEY` (for AI analysis)
- Frontend: `BACKEND_URL` (server-side fetch target, defaults to `http://localhost:8000`)

---

## Roadmap

### Completed

- **Phase 1 — Skill Stats DB**: `agent_skills.json` (29 agents, 851 stats) + `patch_history/*.json` with computed current values
- **Phase 2 — Patch Impact Model**: Similar-case retrieval over 136 historical patches estimates pick/win rate deltas
- **Phase 3 — Patch Simulator**: Virtual patch input -> meta delta prediction -> AI analysis with role-aware comparisons and current-state context
- **Auto-Update Pipeline**: Detect new patch -> crawl ranked + VCT -> rebuild -> reload predictions

### In Progress

- **Patch Prediction Accuracy**: Stage A BA 0.66, Stage B BA 0.78. Stage A has the most room for improvement. Accuracy improves as more acts accumulate
- **Model Enhancement**: Skill ceiling features added; absolute strength features under experiment

---

## Tech Stack

| Component | Technology |
|---|---|
| Data Collection | Python (Playwright, BeautifulSoup) |
| Patch Note Parsing | Claude API |
| Data Processing | pandas, numpy |
| ML | XGBoost, scikit-learn |
| HPO | Optuna (TPE Sampler) |
| Feature Importance | SHAP |
| AI Analysis | Claude Haiku (role-aware prompts, current-state context) |
| Frontend | Next.js 16 (App Router), Tailwind CSS, Oswald + Noto Sans KR |
| API | FastAPI |
| Deployment | Frontend: Vercel · Backend: Railway · DNS: Cloudflare (whosnxt.app / api.whosnxt.app) |
