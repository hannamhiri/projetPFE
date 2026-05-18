# =============================================================
# data_loader.py — Chargement des données depuis ClickHouse
# =============================================================

import pandas as pd
import clickhouse_connect
from config import (
    CLICKHOUSE_HOST, CLICKHOUSE_PORT,
    CLICKHOUSE_USER, CLICKHOUSE_PASSWORD,
    CLICKHOUSE_DATABASE, DATE_START, DATE_END, FREQ
)


def get_client():
    """Créer et retourner un client ClickHouse."""
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )


def load_time_series() -> pd.Series:
    """
    Charger le CA mensuel depuis ClickHouse.
    Retourne une Series avec index DatetimeIndex (freq=MS).
    """
    client = get_client()

    df = client.query_df("""
        SELECT d.Year  AS year,
               d.Month AS month,
               SUM(f.LinePrice) AS total_sales
        FROM gold.fact_sales AS f
        JOIN gold.dim_date   AS d ON f.DateSK = d.DateSK
        WHERE f.DocumentTypeSK IN (4, 1, 5)
          AND f.LinePrice IS NOT NULL
        GROUP BY year, month
        ORDER BY year, month
    """)

    df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))

    df = df[
        (df['date'] >= DATE_START) & (df['date'] <= DATE_END)
    ].reset_index(drop=True)

    ts = df.set_index('date')['total_sales']
    ts.index.freq = FREQ

    print(f'[data_loader] {len(ts)} mois charges')
    print(f'  Periode  : {ts.index[0].strftime("%b %Y")} -> {ts.index[-1].strftime("%b %Y")}')
    print(f'  CA moyen : {ts.mean():,.0f} DT')
    print(f'  CA min   : {ts.min():,.0f} DT ({ts.idxmin().strftime("%b %Y")})')
    print(f'  CA max   : {ts.max():,.0f} DT ({ts.idxmax().strftime("%b %Y")})')

    return ts


if __name__ == '__main__':
    ts = load_time_series()
    print(ts.tail())
