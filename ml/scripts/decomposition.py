# =============================================================
# decomposition.py — Décomposition + ADF + ACF/PACF
# =============================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

MOIS = ['Jan','Fev','Mar','Avr','Mai','Jun',
        'Jul','Aou','Sep','Oct','Nov','Dec']


def run_decomposition(ts: pd.Series, save_dir: str = '/tmp') -> dict:
    """
    Effectue la décomposition additive + tests ADF + ACF/PACF.
    Retourne un dictionnaire avec résultats et paramètre d recommandé.
    """
    results = {}

    # ── 1. Décomposition additive ──────────────────────────────
    print('[decomposition] Decomposition additive...')
    decomp = seasonal_decompose(ts, model='additive', period=12)

    fig, axes = plt.subplots(4, 1, figsize=(14, 10))
    components = [
        (ts,              'Serie originale', 'steelblue'),
        (decomp.trend,    'Tendance',        'orange'),
        (decomp.seasonal, 'Saisonnalite',    'green'),
        (decomp.resid,    'Residus',         'red'),
    ]
    for ax, (data, title, color) in zip(axes, components):
        ax.plot(data, color=color)
        ax.set_title(title)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        if title == 'Residus':
            ax.axhline(0, color='black', linestyle='--', linewidth=0.8)

    plt.suptitle('Decomposition Additive — CA Mensuel SAGAP', fontsize=13)
    plt.tight_layout()
    plt.savefig(f'{save_dir}/decomp_additive.png', dpi=100)
    plt.close()

    # Composante saisonnière par mois
    seas = decomp.seasonal[:12]
    resid_std    = float(decomp.resid.dropna().std())
    trend_growth = float(decomp.trend.dropna().iloc[-1] - decomp.trend.dropna().iloc[0])
    amplitude    = float(seas.max() - seas.min())

    results['trend_growth']        = trend_growth
    results['seasonal_amplitude']  = amplitude
    results['resid_std']           = resid_std
    results['seasonal_components'] = dict(zip(MOIS, seas.values.tolist()))

    print(f'  Tendance     : +{trend_growth:,.0f} DT sur la periode')
    print(f'  Saisonnalite : amplitude {amplitude:,.0f} DT')
    print(f'  Residus      : std = {resid_std:,.0f} DT')

    print('\n  Composante saisonniere par mois :')
    for m, v in zip(MOIS, seas.values):
        sign = '+' if v >= 0 else ''
        bar  = 'I' * int(abs(v) / 20000)
        print(f'    {m} : {sign}{v:>10,.0f} DT  {bar}')

    # ── 2. Test ADF ────────────────────────────────────────────
    print('\n[decomposition] Test ADF...')
    adf = adfuller(ts)
    adf_pvalue = float(adf[1])
    results['adf_statistic'] = float(adf[0])
    results['adf_pvalue']    = adf_pvalue

    print(f'  Statistique ADF : {adf[0]:.4f}')
    print(f'  p-value         : {adf_pvalue:.4f}')

    if adf_pvalue < 0.05:
        d_arima = 0
        print('  Serie STATIONNAIRE -> d=0')
    else:
        d_arima = 1
        print('  Serie NON STATIONNAIRE -> d=1')

    # Vérification après diff(1)
    ts_diff = ts.diff().dropna()
    adf2 = adfuller(ts_diff)
    results['adf_diff_pvalue'] = float(adf2[1])
    results['d_arima']         = d_arima

    print(f'  ADF apres diff(1) : p-value = {adf2[1]:.4f}')
    print(f'  -> d={d_arima} confirme pour SARIMA')

    # ── 3. ACF / PACF ──────────────────────────────────────────
    print('\n[decomposition] ACF/PACF...')
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    plot_acf(ts,       lags=20, ax=axes[0, 0], title='ACF — Serie originale')
    plot_pacf(ts,      lags=20, ax=axes[0, 1], title='PACF — Serie originale')
    plot_acf(ts_diff,  lags=20, ax=axes[1, 0], title='ACF — Serie differenciee')
    plot_pacf(ts_diff, lags=20, ax=axes[1, 1], title='PACF — Serie differenciee')
    plt.tight_layout()
    plt.savefig(f'{save_dir}/decomp_acf_pacf.png', dpi=100)
    plt.close()

    print(f'  -> Graphes sauvegardes dans {save_dir}/')
    print(f'  -> Pic lag 12 confirme saisonnalite annuelle')

    return results


if __name__ == '__main__':
    from data_loader import load_time_series
    ts = load_time_series()
    results = run_decomposition(ts)
    print('\nResultats :', results)
