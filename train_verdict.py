"""
Patch Verdict - Model Training
XGBoost + Optuna HPO + Stratified K-Fold + SHAP
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score
import xgboost as xgb
import optuna
import shap
import joblib

optuna.logging.set_verbosity(optuna.logging.WARNING)

# ─── 상수 ────────────────────────────────────────────────────────────────────

LABEL_ORDER = ["INEFFECTIVE", "BALANCED", "EFFECTIVE", "EXCESSIVE"]

CAT_FEATURES = [
    "direction", "trigger_type", "agent_role", "agent_subrole", "last_patch_direction",
]

# VCT 기반 레이블이 더 신뢰 → 가중치 높임
SOURCE_WEIGHT = {"vct": 1.0, "rank": 0.6, "none": 0.0}

# ─── 데이터 준비 ─────────────────────────────────────────────────────────────

def load_and_prepare():
    df = pd.read_csv("training_data.csv")
    print(f"전체 케이스: {len(df)}  /  레이블 분포:")
    print(df["verdict_label"].value_counts().to_string())

    # PENDING 제외
    df = df[df["verdict_label"] != "PENDING"].copy()
    print(f"\n학습 케이스: {len(df)} (PENDING 제외)")

    # 레이블 인코딩
    le = LabelEncoder()
    le.fit(LABEL_ORDER)
    df["y"] = le.transform(df["verdict_label"])

    # 샘플 가중치 (VCT=1.0, rank=0.6)
    df["sample_weight"] = df["verdict_source"].map(SOURCE_WEIGHT).fillna(0.5)

    # 카테고리형 인코딩 (OrdinalEncoder → XGBoost enable_categorical 사용)
    oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    for col in CAT_FEATURES:
        if col in df.columns:
            df[col] = oe.fit_transform(df[[col]])

    # 피처 컬럼 결정
    drop_cols = ["agent", "patch", "patch_act", "verdict_label", "verdict_source", "y", "sample_weight"]
    feat_cols = [c for c in df.columns if c not in drop_cols]

    X = df[feat_cols].values.astype(np.float32)
    y = df["y"].values
    w = df["sample_weight"].values

    print(f"\n피처 수: {len(feat_cols)}")
    print(f"레이블 분포 (학습셋): {dict(zip(LABEL_ORDER, np.bincount(y)))}")

    return X, y, w, feat_cols, le, df


# ─── Optuna HPO ──────────────────────────────────────────────────────────────

def run_hpo(X, y, w, n_trials=80):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    def objective(trial):
        params = {
            "n_estimators":      trial.suggest_int("n_estimators", 100, 600),
            "max_depth":         trial.suggest_int("max_depth", 2, 6),
            "learning_rate":     trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
            "subsample":         trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "min_child_weight":  trial.suggest_int("min_child_weight", 1, 10),
            "gamma":             trial.suggest_float("gamma", 0.0, 2.0),
            "reg_alpha":         trial.suggest_float("reg_alpha", 1e-4, 5.0, log=True),
            "reg_lambda":        trial.suggest_float("reg_lambda", 1e-4, 5.0, log=True),
            "objective":         "multi:softmax",
            "num_class":         4,
            "eval_metric":       "mlogloss",
            "use_label_encoder": False,
            "random_state":      42,
            "verbosity":         0,
        }
        model = xgb.XGBClassifier(**params)

        scores = []
        for train_idx, val_idx in cv.split(X, y):
            model.fit(
                X[train_idx], y[train_idx],
                sample_weight=w[train_idx],
                eval_set=[(X[val_idx], y[val_idx])],
                verbose=False,
            )
            preds = model.predict(X[val_idx])
            scores.append(balanced_accuracy_score(y[val_idx], preds))
        return np.mean(scores)

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    print(f"\n[HPO 완료] best balanced_accuracy: {study.best_value:.4f}")
    print(f"best params: {study.best_params}")
    return study.best_params


# ─── 최종 평가 ───────────────────────────────────────────────────────────────

def final_eval(X, y, w, best_params):
    params = {
        **best_params,
        "objective":         "multi:softmax",
        "num_class":         4,
        "eval_metric":       "mlogloss",
        "use_label_encoder": False,
        "random_state":      42,
        "verbosity":         0,
    }
    model = xgb.XGBClassifier(**params)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    all_preds = np.zeros(len(y), dtype=int)
    fold_scores = []

    for fold, (train_idx, val_idx) in enumerate(cv.split(X, y), 1):
        model.fit(
            X[train_idx], y[train_idx],
            sample_weight=w[train_idx],
            eval_set=[(X[val_idx], y[val_idx])],
            verbose=False,
        )
        preds = model.predict(X[val_idx])
        all_preds[val_idx] = preds
        ba = balanced_accuracy_score(y[val_idx], preds)
        fold_scores.append(ba)
        print(f"  Fold {fold}: balanced_accuracy={ba:.4f}")

    print(f"\n평균 balanced_accuracy: {np.mean(fold_scores):.4f} ± {np.std(fold_scores):.4f}")
    print(f"\n[분류 리포트]")
    print(classification_report(y, all_preds, target_names=LABEL_ORDER))
    print(f"[혼동 행렬] (행=실제, 열=예측)")
    cm = confusion_matrix(y, all_preds)
    cm_df = pd.DataFrame(cm, index=LABEL_ORDER, columns=LABEL_ORDER)
    print(cm_df.to_string())

    return model, fold_scores, all_preds


# ─── 전체 데이터로 최종 모델 학습 ────────────────────────────────────────────

def train_final_model(X, y, w, best_params):
    params = {
        **best_params,
        "objective":         "multi:softmax",
        "num_class":         4,
        "eval_metric":       "mlogloss",
        "use_label_encoder": False,
        "random_state":      42,
        "verbosity":         0,
    }
    model = xgb.XGBClassifier(**params)
    model.fit(X, y, sample_weight=w)
    return model


# ─── SHAP 피처 중요도 ─────────────────────────────────────────────────────────

def shap_importance(model, X, feat_cols):
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X)  # (n_samples, n_features, n_classes) or list

    # multi-class SHAP: mean abs across classes
    if isinstance(shap_vals, list):
        mean_abs = np.mean([np.abs(sv) for sv in shap_vals], axis=0).mean(axis=0)
    else:
        mean_abs = np.abs(shap_vals).mean(axis=(0, 2)) if shap_vals.ndim == 3 else np.abs(shap_vals).mean(axis=0)

    imp = pd.Series(mean_abs, index=feat_cols).sort_values(ascending=False)
    print("\n[SHAP 피처 중요도 Top 20]")
    print(imp.head(20).round(4).to_string())
    return imp


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("Patch Verdict - Model Training")
    print("=" * 65 + "\n")

    X, y, w, feat_cols, le, df = load_and_prepare()

    print("\n[HPO 실행 중... 80 trials]")
    best_params = run_hpo(X, y, w, n_trials=80)

    print("\n[5-Fold 교차검증]")
    model, fold_scores, oof_preds = final_eval(X, y, w, best_params)

    print("\n[전체 데이터 최종 모델 학습]")
    final_model = train_final_model(X, y, w, best_params)
    joblib.dump(final_model, "verdict_model.pkl")
    print("저장: verdict_model.pkl")

    print("\n[SHAP 분석]")
    shap_imp = shap_importance(final_model, X, feat_cols)
    shap_imp.to_csv("shap_importance.csv", header=["shap_mean_abs"])
    print("저장: shap_importance.csv")

    # OOF 예측 결과 저장
    result_df = df[["agent", "patch", "verdict_label", "verdict_source"]].copy()
    result_df["oof_pred"] = le.inverse_transform(oof_preds)
    result_df["correct"] = result_df["verdict_label"] == result_df["oof_pred"]
    result_df.to_csv("oof_predictions.csv", index=False, encoding="utf-8-sig")
    print("저장: oof_predictions.csv")

    print(f"\n정확도 (단순): {result_df['correct'].mean():.2%}")
    print(f"\n[오분류 케이스]")
    wrong = result_df[~result_df["correct"]][["agent","patch","verdict_label","oof_pred","verdict_source"]]
    print(wrong.to_string(index=False))

    return final_model, shap_imp


if __name__ == "__main__":
    main()
