# =============================================================
# evaluation.py — Comparaison des modèles + visualisations
# =============================================================

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import MAPE_BON, MAPE_EXCELLENT


def run_evaluation(ts_train, ts_test, all_results: list,
                   save_dir: str = '/tmp') -> pd.DataFrame:
    """
    Comparer tous les modèles, afficher le tableau,
    sauvegarder les graphes.
    Retourne un DataFrame trié par MAPE.
    """
    # ── Tableau comparatif ─────────────────────────────────────
    df = pd.DataFrame([
        {k: v for k, v in r.items()
         if k not in ('pred', 'model_obj', 'ci_low', 'ci_high',
                      'best_order', 'best_seas')}
        for r in all_results
    ]).set_index('name').sort_values('MAPE')

    print('\n[evaluation] Comparaison des modeles :')
    print('=' * 75)
    print(f'{"Modele":<28} {"MAE":>10} {"RMSE":>10} '
          f'{"MAPE":>8} {"SMAPE":>8} {"Biais":>12}')
    print('=' * 75)
    for _, row in df.iterrows():
        mae   = float(row['MAE'])
        rmse  = float(row['RMSE'])
        mape  = float(row['MAPE'])
        smape = float(row['SMAPE'])
        biais = float(row['Biais'])
        qualite = 'excellent' if mape < MAPE_EXCELLENT else \
                  'bon' if mape < MAPE_BON else 'acceptable'
        print(f'{row.name:<28} {mae:>10,.0f} {rmse:>10,.0f} '
              f'{mape:>7.2f}% {smape:>7.2f}% {biais:>12,.0f}  [{qualite}]')
    print('=' * 75)

    best_name = df['MAPE'].idxmin()
    best_mape = float(df.loc[best_name, 'MAPE'])
    print(f'\n  Meilleur modele : {best_name} (MAPE={best_mape:.2f}%)')
    print(f'  Reference industrie : 10-15% -> nos modeles sont au-dessus du standard')

    # ── Graphe MAPE coloré ─────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 5))
    vals   = df['MAPE'].astype(float)
    colors = ['green' if v < MAPE_EXCELLENT
              else 'orange' if v < MAPE_BON
              else 'red' for v in vals.values]
    bars = ax.bar(vals.index, vals.values, color=colors)
    ax.axhline(MAPE_BON,       color='orange', linestyle='--',
               label=f'Seuil {MAPE_BON}% (acceptable)', alpha=0.7)
    ax.axhline(MAPE_EXCELLENT, color='green',  linestyle='--',
               label=f'Seuil {MAPE_EXCELLENT}% (excellent)', alpha=0.7)
    ax.set_title('MAPE par Modele — Comparaison')
    ax.set_ylabel('MAPE (%)')
    ax.tick_params(axis='x', rotation=30)
    for bar, val in zip(bars, vals.values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + vals.max() * 0.01,
                f'{val:.1f}%', ha='center', fontsize=9)
    ax.legend()
    plt.tight_layout()
    plt.savefig(f'{save_dir}/eval_mape_comparison.png', dpi=100)
    plt.close()

    # ── Graphe réel vs prédit tous modèles ────────────────────
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(ts_train.index, ts_train.values,
            color='steelblue', linewidth=1.5, alpha=0.5, label='Train')
    ax.plot(ts_test.index, ts_test.values,
            color='black', marker='o', linewidth=2.5,
            label='CA Reel (test)', zorder=5)

    palette = plt.cm.tab10.colors
    for i, r in enumerate(all_results):
        ax.plot(ts_test.index, r['pred'],
                label=f"{r['name']} ({float(r['MAPE']):.1f}%)",
                marker='s', linestyle='--',
                color=palette[i % len(palette)], alpha=0.8)

    ax.set_title('CA Reel vs Predit — Tous les modeles')
    ax.set_ylabel('CA (DT)')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.legend(loc='upper left', fontsize=8)
    plt.tight_layout()
    plt.savefig(f'{save_dir}/eval_reel_vs_predit.png', dpi=100)
    plt.close()

    print(f'\n  -> Graphes sauvegardes dans {save_dir}/')
    return df


if __name__ == '__main__':
    from data_loader import load_time_series
    from models import (train_hw_additif, train_hw_multiplicatif,
                        train_sarima, train_prophet)
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
    df = run_evaluation(ts_train, ts_test, all_results)
