# =============================================================
# prediction.py — Prévision 12 mois + sauvegarde ClickHouse
# =============================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import clickhouse_connect
import warnings
warnings.filterwarnings('ignore')

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet

from config import (
    CLICKHOUSE_HOST, CLICKHOUSE_PORT,
    CLICKHOUSE_USER, CLICKHOUSE_PASSWORD,
    CLICKHOUSE_DATABASE, SEASONAL_PERIODS, N_PRED,
    OUTPUT_TABLE
)


def run_prediction(ts: pd.Series, best_result: dict,
                   save_dir: str = '/tmp') -> pd.DataFrame:
    """
    Réentraîner le meilleur modèle sur toute la série
    et prédire N_PRED mois.
    Retourne un DataFrame avec les prédictions.
    """
    best_name = best_result['name']
    print(f'\n[prediction] Reentraînement de {best_name} sur {len(ts)} mois...')

    forecast_vals = _forecast(ts, best_result)

    future_dates = pd.date_range(
        ts.index[-1] + pd.DateOffset(months=1),
        periods=N_PRED, freq='MS'
    )

    df_pred = pd.DataFrame({
        'date':            future_dates,
        'year':            future_dates.year,
        'month':           future_dates.month,
        'predicted_sales': forecast_vals,
        'is_prediction':   1
    })

    # ── Résumé ─────────────────────────────────────────────────
    ca_2024    = ts[ts.index.year == 2024].sum()
    ca_2025    = ts[ts.index.year == 2025].sum()
    ca_prev    = df_pred['predicted_sales'].sum()
    croissance = (ca_prev - ca_2025) / ca_2025 * 100

    print(f'\n  Predictions {best_name} :')
    for _, row in df_pred.iterrows():
        print(f'    {row["date"].strftime("%b %Y")} -> {row["predicted_sales"]:>15,.2f} DT')

    print(f'\n  {"="*55}')
    print(f'  CA reel 2024      : {ca_2024:>15,.2f} DT')
    print(f'  CA reel 2025      : {ca_2025:>15,.2f} DT')
    print(f'  CA prevu          : {ca_prev:>15,.2f} DT')
    print(f'  Croissance 25->26 : {croissance:>15.2f} %')
    print(f'  Modele            : {best_name}')
    print(f'  MAPE test         : {best_result["MAPE"]:.2f}%')
    print(f'  {"="*55}')

    # ── Graphe Plotly-like matplotlib ─────────────────────────
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(ts.index, ts.values,
            color='steelblue', marker='o', linewidth=2, label='CA Reel')
    ax.plot(df_pred['date'], df_pred['predicted_sales'],
            color='orange', marker='s', linestyle='--',
            linewidth=2, label=f'CA Predit ({best_name})')
    ax.axvline(ts.index[-1], color='red', linestyle=':', linewidth=1.5,
               label=f'Fin donnees reelles ({ts.index[-1].strftime("%b %Y")})')
    ax.set_title(f'CA Reel + Prevision 12 mois — {best_name} (MAPE={best_result["MAPE"]:.2f}%)')
    ax.set_ylabel('CA (DT)')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.legend()
    plt.tight_layout()
    plt.savefig(f'{save_dir}/prediction_12mois.png', dpi=100)
    plt.close()

    # ── Graphe CA annuel ───────────────────────────────────────
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    labels = ['2024 (reel)', '2025 (reel)', '2026 (predit)']
    values = [ca_2024, ca_2025, ca_prev]
    colors = ['steelblue', 'steelblue', 'orange']
    ax2.bar(labels, values, color=colors)
    for i, v in enumerate(values):
        ax2.text(i, v + max(values) * 0.01,
                 f'{v:,.0f} DT', ha='center', fontsize=9)
    ax2.set_title('CA Annuel : Reel vs Prevu')
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.tight_layout()
    plt.savefig(f'{save_dir}/prediction_ca_annuel.png', dpi=100)
    plt.close()

    print(f'  -> Graphes sauvegardes dans {save_dir}/')
    return df_pred


def _forecast(ts: pd.Series, best_result: dict) -> np.ndarray:
    """Réentraîner et prédire selon le type de modèle."""
    name = best_result['name']

    if 'HW-Additif' in name:
        fm = ExponentialSmoothing(
            ts, trend='add', seasonal='add', seasonal_periods=SEASONAL_PERIODS
        ).fit()
        return fm.forecast(N_PRED).values

    elif 'HW-Multiplicatif' in name:
        fm = ExponentialSmoothing(
            ts, trend='add', seasonal='mul', seasonal_periods=SEASONAL_PERIODS
        ).fit()
        return fm.forecast(N_PRED).values

    elif 'SARIMA' in name:
        fm = SARIMAX(
            ts,
            order=best_result['best_order'],
            seasonal_order=best_result['best_seas'],
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit(disp=False)
        return fm.forecast(steps=N_PRED).values

    elif 'Prophet' in name:
        df_full = pd.DataFrame({'ds': ts.index, 'y': ts.values})
        fm = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode='additive'
        )
        fm.fit(df_full)
        future = fm.make_future_dataframe(periods=N_PRED, freq='MS')
        fc     = fm.predict(future)
        return fc['yhat'].iloc[-N_PRED:].values

    else:
        raise ValueError(f'Modele inconnu : {name}')


def save_to_clickhouse(df_pred: pd.DataFrame):
    """Écrire les prédictions dans ClickHouse gold.ml_predictions."""
    print('\n[prediction] Ecriture dans ClickHouse...')

    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )

    client.command(f'DROP TABLE IF EXISTS {OUTPUT_TABLE}')
    client.command(f"""
        CREATE TABLE {OUTPUT_TABLE} (
            date             Date,
            year             Int32,
            month            Int32,
            predicted_sales  Float64,
            is_prediction    Int8
        ) ENGINE = MergeTree()
        ORDER BY date
    """)

    df_insert = df_pred[['date', 'year', 'month',
                          'predicted_sales', 'is_prediction']].copy()
    df_insert['date'] = pd.to_datetime(df_insert['date']).dt.date

    client.insert_df(OUTPUT_TABLE, df_insert)

    check = client.query_df(f'SELECT * FROM {OUTPUT_TABLE} ORDER BY date')
    print(f'  -> {len(check)} predictions ecrites dans {OUTPUT_TABLE}')
    print(check.to_string(index=False))


if __name__ == '__main__':
    from data_loader import load_time_series
    from models import (train_hw_additif, train_hw_multiplicatif,
                        train_sarima, train_prophet, select_best)
    from config import N_TEST

    ts       = load_time_series()
    ts_train = ts.iloc[:-N_TEST]
    ts_test  = ts.iloc[-N_TEST:]

    all_results = [
        train_hw_additif(ts_train, ts_test, N_TEST),
        train_hw_multiplicatif(ts_train, ts_test, N_TEST),
        train_sarima(ts_train, ts_test, N_TEST),
        train_prophet(ts_train, ts_test, N_TEST),
    ]

    best    = select_best(all_results)
    df_pred = run_prediction(ts, best)
    save_to_clickhouse(df_pred)
