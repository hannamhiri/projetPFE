# =============================================================
# pipeline.py — Pipeline ML complet SAGAP
# Load -> EDA -> Decomposition -> Models -> Evaluation -> Prediction
# =============================================================

import os, sys, time, mlflow
sys.path.insert(0, os.path.dirname(__file__))

from config        import MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT, N_TEST
from data_loader   import load_time_series
from eda           import run_eda
from decomposition import run_decomposition
from models        import run_h1_modeling, select_best
from evaluation    import run_evaluation
from prediction    import run_prediction, save_to_clickhouse

SAVE_DIR = '/tmp/ml_outputs'
os.makedirs(SAVE_DIR, exist_ok=True)


def run_pipeline():
    start = time.time()
    print('=' * 60)
    print('  PIPELINE ML SAGAP — Prevision CA Mensuel')
    print('=' * 60)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    # ── ETAPE 1 : Load ────────────────────────────────────────
    print('\n>>> ETAPE 1 — Load Raw Data')
    ts = load_time_series()

    # ── ETAPE 2 : EDA ─────────────────────────────────────────
    print('\n>>> ETAPE 2 — EDA')
    eda_stats = run_eda(ts, save_dir=SAVE_DIR)

    # ── ETAPE 3 : Decomposition ───────────────────────────────
    print('\n>>> ETAPE 3 — Decomposition + ADF + ACF/PACF')
    decomp_results = run_decomposition(ts, save_dir=SAVE_DIR)

    # ── Split ─────────────────────────────────────────────────
    ts_train = ts.iloc[:-N_TEST]
    ts_test  = ts.iloc[-N_TEST:]
    print(f'\n  Split : Train={len(ts_train)} | Test={len(ts_test)} mois')

    # ── ETAPE 4 : Modelisation ────────────────────────────────
    # Logique : HW vs Prophet (add/mul) → gagnant vs SARIMA
    print('\n>>> ETAPE 4 — Modelisation H1 : HW vs Prophet vs SARIMA')
    h1_results = run_h1_modeling(ts_train, ts_test, N_TEST)
    all_results = h1_results['all']

    # ── ETAPE 5 : Evaluation ──────────────────────────────────
    print('\n>>> ETAPE 5 — Evaluation')
    df_results = run_evaluation(ts_train, ts_test, all_results, save_dir=SAVE_DIR)

    # ── ETAPE 6 : Prediction ──────────────────────────────────
    print('\n>>> ETAPE 6 — Prediction 12 mois')
    best    = select_best(all_results)
    df_pred = run_prediction(ts, best, save_dir=SAVE_DIR)
    save_to_clickhouse(df_pred)

    elapsed = time.time() - start
    print(f'\n{"="*60}')
    print(f'  PIPELINE TERMINE en {elapsed:.1f}s')
    print(f'  Meilleur modele : {best["name"]} (MAPE={best["MAPE"]:.2f}%)')
    print(f'  CA prevu 12 mois : {df_pred["predicted_sales"].sum():,.0f} DT')
    print(f'  MLflow : {MLFLOW_TRACKING_URI}')
    print(f'  Graphes : {SAVE_DIR}/')
    print(f'{"="*60}')

    return {'ts':ts,'eda':eda_stats,'decomp':decomp_results,
            'h1':h1_results,'df_results':df_results,
            'best':best,'df_pred':df_pred}


if __name__ == '__main__':
    run_pipeline()
