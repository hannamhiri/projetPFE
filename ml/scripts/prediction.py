# =============================================================
# prediction.py — Prevision 12 mois + sauvegarde ClickHouse
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
    CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER,
    CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE,
    SEASONAL_PERIODS, N_PRED, OUTPUT_TABLE
)


def run_prediction(ts, best_result, save_dir='/tmp'):
    name = best_result['name']
    print(f'\n[prediction] Reentrainement de {name} sur {len(ts)} mois...')
    forecast_vals = _forecast(ts, best_result)

    future_dates = pd.date_range(
        ts.index[-1] + pd.DateOffset(months=1), periods=N_PRED, freq='MS'
    )
    df_pred = pd.DataFrame({
        'date':            future_dates,
        'year':            future_dates.year,
        'month':           future_dates.month,
        'predicted_sales': forecast_vals,
        'is_prediction':   1
    })

    ca_2025    = ts[ts.index.year == 2025].sum()
    ca_prev    = df_pred['predicted_sales'].sum()
    croissance = (ca_prev - ca_2025) / ca_2025 * 100

    print(f'\n  Predictions {name} :')
    for _, row in df_pred.iterrows():
        print(f'    {row["date"].strftime("%b %Y")} -> {row["predicted_sales"]:>15,.2f} DT')

    print(f'\n  {"="*50}')
    print(f'  CA reel 2025      : {ca_2025:>15,.2f} DT')
    print(f'  CA prevu 2026     : {ca_prev:>15,.2f} DT')
    print(f'  Croissance        : {croissance:>15.2f} %')
    print(f'  Modele            : {name} (MAPE={best_result["MAPE"]:.2f}%)')
    print(f'  {"="*50}')

    # Graphe
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(ts.index, ts.values,
            color='steelblue', marker='o', linewidth=2, label='CA Reel')
    ax.plot(df_pred['date'], df_pred['predicted_sales'],
            color='orange', marker='s', linestyle='--',
            linewidth=2, label=f'CA Predit ({name})')
    ax.axvline(ts.index[-1], color='red', linestyle=':', linewidth=1.5,
               label=f'Fin donnees reelles ({ts.index[-1].strftime("%b %Y")})')
    ax.set_title(f'CA Reel + Prevision 12 mois — {name} (MAPE={best_result["MAPE"]:.2f}%)')
    ax.set_ylabel('CA (DT)')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.legend()
    plt.tight_layout()
    plt.savefig(f'{save_dir}/prediction_12mois.png', dpi=100)
    plt.close()
    print(f'  -> Graphe sauvegarde : {save_dir}/prediction_12mois.png')
    return df_pred


def _forecast(ts, best_result):
    name = best_result['name']

    if 'HW-Add' in name:
        fm = ExponentialSmoothing(
            ts, trend='add', seasonal='add', seasonal_periods=SEASONAL_PERIODS
        ).fit()
        return fm.forecast(N_PRED).values

    elif 'HW-Mul' in name:
        fm = ExponentialSmoothing(
            ts, trend='add', seasonal='mul', seasonal_periods=SEASONAL_PERIODS
        ).fit()
        return fm.forecast(N_PRED).values

    elif 'SARIMA' in name:
        fm = SARIMAX(
            ts, order=best_result['best_order'],
            seasonal_order=best_result['best_seas'],
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit(disp=False)
        return fm.forecast(steps=N_PRED).values

    elif 'Prophet-Mul' in name:
        df_full = pd.DataFrame({'ds': ts.index, 'y': ts.values})
        fm = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                     daily_seasonality=False, seasonality_mode='multiplicative')
        fm.fit(df_full)
        fc = fm.predict(fm.make_future_dataframe(periods=N_PRED, freq='MS'))
        return fc['yhat'].iloc[-N_PRED:].values

    elif 'Prophet-Add' in name:
        df_full = pd.DataFrame({'ds': ts.index, 'y': ts.values})
        fm = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                     daily_seasonality=False, seasonality_mode='additive')
        fm.fit(df_full)
        fc = fm.predict(fm.make_future_dataframe(periods=N_PRED, freq='MS'))
        return fc['yhat'].iloc[-N_PRED:].values

    else:
        raise ValueError(f'Modele inconnu : {name}')


def save_to_clickhouse(df_pred):
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
    df_insert = df_pred[['date','year','month','predicted_sales','is_prediction']].copy()
    df_insert['date'] = pd.to_datetime(df_insert['date']).dt.date
    client.insert_df(OUTPUT_TABLE, df_insert)
    check = client.query_df(f'SELECT * FROM {OUTPUT_TABLE} ORDER BY date')
    print(f'  -> {len(check)} predictions ecrites dans {OUTPUT_TABLE}')
