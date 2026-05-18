# =============================================================
# pipeline.py — Pipeline ML complet SAGAP
# Exécute : Load -> EDA -> Decomposition -> Models -> Evaluation -> Prediction
# =============================================================

import os
import sys
import time
import mlflow

# Ajouter le dossier scripts au path
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT, N_TEST
)
from data_loader   import load_time_series
from eda           import run_eda
from decomposition import run_decomposition
from models        import (train_hw_additif, train_hw_multiplicatif,
                            train_sarima, train_prophet, select_best)
from evaluation    import run_evaluation
from prediction    import run_prediction, save_to_clickhouse

# ── Dossier pour les graphes ──────────────────────────────────
SAVE_DIR = '/tmp/ml_outputs'
os.makedirs(SAVE_DIR, exist_ok=True)


def run_pipeline():
    """Exécuter le pipeline ML complet."""
    start = time.time()

    print('=' * 60)
    print('  PIPELINE ML SAGAP — Prévision CA Mensuel')
    print('=' * 60)

    # ── MLflow setup ──────────────────────────────────────────
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    # ── ÉTAPE 1 : Load Raw Data ───────────────────────────────
    print('\n>>> ETAPE 1 — Load Raw Data')
    ts = load_time_series()

    # ── ÉTAPE 2 : EDA ─────────────────────────────────────────
    print('\n>>> ETAPE 2 — Exploratory Data Analysis')
    eda_stats = run_eda(ts, save_dir=SAVE_DIR)

    # ── ÉTAPE 3 : Decomposition ───────────────────────────────
    print('\n>>> ETAPE 3 — Decomposition + ADF + ACF/PACF')
    decomp_results = run_decomposition(ts, save_dir=SAVE_DIR)

    # ── Split Train / Test ────────────────────────────────────
    ts_train = ts.iloc[:-N_TEST]
    ts_test  = ts.iloc[-N_TEST:]
    print(f'\n  Split : Train={len(ts_train)} mois | Test={len(ts_test)} mois')

    # ── ÉTAPE 4 : Model Selection & Fitting ───────────────────
    print('\n>>> ETAPE 4 — Model Selection and Fitting')
    all_results = []
    all_results.append(train_hw_additif(ts_train, ts_test, N_TEST))
    all_results.append(train_hw_multiplicatif(ts_train, ts_test, N_TEST))
    all_results.append(train_sarima(ts_train, ts_test, N_TEST))
    all_results.append(train_prophet(ts_train, ts_test, N_TEST))

    # ── ÉTAPE 5 : Evaluation ──────────────────────────────────
    print('\n>>> ETAPE 5 — Model Evaluation')
    df_results = run_evaluation(ts_train, ts_test, all_results,
                                save_dir=SAVE_DIR)

    # ── ÉTAPE 6 : Prediction ──────────────────────────────────
    print('\n>>> ETAPE 6 — Model Prediction and Forecasting')
    best    = select_best(all_results)
    df_pred = run_prediction(ts, best, save_dir=SAVE_DIR)
    save_to_clickhouse(df_pred)

    # ── Résumé final ──────────────────────────────────────────
    elapsed = time.time() - start
    print(f'\n{"=" * 60}')
    print(f'  PIPELINE TERMINE en {elapsed:.1f}s')
    print(f'  Meilleur modele : {best["name"]} (MAPE={best["MAPE"]:.2f}%)')
    print(f'  CA prevu        : {df_pred["predicted_sales"].sum():,.0f} DT')
    print(f'  MLflow          : {MLFLOW_TRACKING_URI}')
    print(f'  Graphes         : {SAVE_DIR}/')
    print(f'{"=" * 60}')

    return {
        'ts':            ts,
        'eda_stats':     eda_stats,
        'decomp':        decomp_results,
        'all_results':   all_results,
        'df_results':    df_results,
        'best':          best,
        'df_pred':       df_pred,
    }


if __name__ == '__main__':
    run_pipeline()
