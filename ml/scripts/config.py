# =============================================================
# config.py — Configuration globale du pipeline ML SAGAP
# =============================================================

# ── ClickHouse ────────────────────────────────────────────────
CLICKHOUSE_HOST     = 'clickhouse'
CLICKHOUSE_PORT     = 8123
CLICKHOUSE_USER     = 'default'
CLICKHOUSE_PASSWORD = 'clickhouse123'
CLICKHOUSE_DATABASE = 'gold'

# ── MLflow ────────────────────────────────────────────────────
MLFLOW_TRACKING_URI = 'http://mlflow:5000'
MLFLOW_EXPERIMENT   = 'TimeSeries_Forecasting'

# ── Données ───────────────────────────────────────────────────
DATE_START  = '2022-01-01'
DATE_END    = '2026-01-01'
FREQ        = 'MS'           # Month Start

# ── Modèles ───────────────────────────────────────────────────
N_TEST           = 6         # Mois de test
N_PRED           = 12        # Mois à prédire
SEASONAL_PERIODS = 12        # Saisonnalité annuelle

# ── SARIMA ────────────────────────────────────────────────────
SARIMA_P_RANGE = [0, 1]
SARIMA_D_RANGE = [1]         # Forcé à 1 (ADF confirmé)
SARIMA_Q_RANGE = [0, 1]
SARIMA_SEASONAL = (1, 1, 1, 12)

# ── Seuils évaluation ─────────────────────────────────────────
MAPE_EXCELLENT  = 5.0
MAPE_BON        = 10.0

# ── ClickHouse output ─────────────────────────────────────────
OUTPUT_TABLE = 'gold.ml_predictions'

# For best model retriraining
REGISTRY_NAME = 'TimeSeries_SalesForcast'