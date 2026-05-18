# =============================================================
# eda.py — Exploratory Data Analysis
# =============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')   # mode non-interactif pour Dagster

MOIS = ['Jan','Fev','Mar','Avr','Mai','Jun',
        'Jul','Aou','Sep','Oct','Nov','Dec']


def run_eda(ts: pd.Series, save_dir: str = '/tmp') -> dict:
    """
    Effectue l'EDA complète sur la série temporelle.
    Sauvegarde les graphes dans save_dir.
    Retourne un dictionnaire de statistiques.
    """
    stats = {}

    # ── 1. Statistiques descriptives ──────────────────────────
    stats['n_mois']    = len(ts)
    stats['ca_moyen']  = float(ts.mean())
    stats['ca_median'] = float(ts.median())
    stats['ca_std']    = float(ts.std())
    stats['ca_min']    = float(ts.min())
    stats['ca_max']    = float(ts.max())
    stats['cv_pct']    = float(ts.std() / ts.mean() * 100)
    stats['date_min']  = ts.idxmin().strftime('%b %Y')
    stats['date_max']  = ts.idxmax().strftime('%b %Y')

    print('[eda] Statistiques descriptives :')
    print(f'  Nombre de mois : {stats["n_mois"]}')
    print(f'  CA moyen       : {stats["ca_moyen"]:>15,.0f} DT')
    print(f'  CA mediane     : {stats["ca_median"]:>15,.0f} DT')
    print(f'  Ecart-type     : {stats["ca_std"]:>15,.0f} DT')
    print(f'  CA minimum     : {stats["ca_min"]:>15,.0f} DT ({stats["date_min"]})')
    print(f'  CA maximum     : {stats["ca_max"]:>15,.0f} DT ({stats["date_max"]})')
    print(f'  Coefficient CV : {stats["cv_pct"]:>15.1f} % (variabilite relative)')

    # ── 2. Série brute ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(ts.index, ts.values, color='steelblue', marker='o', linewidth=2)
    ax.axhline(ts.mean(), color='red', linestyle='--',
               label=f'Moyenne : {ts.mean():,.0f} DT')
    ax.fill_between(ts.index,
                    ts.mean() - ts.std(),
                    ts.mean() + ts.std(),
                    alpha=0.1, color='red', label=f'+-1 std ({ts.std():,.0f} DT)')
    ax.set_title('CA Mensuel SAGAP — Jan 2022 -> Jan 2026')
    ax.set_ylabel('CA (DT)')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.legend()
    plt.tight_layout()
    plt.savefig(f'{save_dir}/eda_serie_brute.png', dpi=100)
    plt.close()
    print(f'  -> Graphe sauvegarde : {save_dir}/eda_serie_brute.png')

    # ── 3. Saisonnalité mensuelle ──────────────────────────────
    monthly_mean = ts.groupby(ts.index.month).mean()
    monthly_std  = ts.groupby(ts.index.month).std()

    mois_forts   = [MOIS[i] for i in monthly_mean.nlargest(3).index - 1]
    mois_faibles = [MOIS[i] for i in monthly_mean.nsmallest(3).index - 1]
    stats['mois_forts']   = mois_forts
    stats['mois_faibles'] = mois_faibles
    stats['amplitude_saisonniere'] = float(monthly_mean.max() - monthly_mean.min())

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].bar(MOIS, monthly_mean.values, color='steelblue')
    axes[0].errorbar(MOIS, monthly_mean.values, yerr=monthly_std.values,
                     fmt='none', color='red', capsize=4)
    axes[0].set_title('CA Moyen par Mois (+-std)')
    axes[0].set_ylabel('CA (DT)')
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    axes[0].tick_params(axis='x', rotation=30)

    ts_df = ts.to_frame()
    ts_df['mois'] = ts.index.month
    ts_df.boxplot(column='total_sales', by='mois', ax=axes[1])
    axes[1].set_title('Distribution CA par Mois')
    axes[1].set_xlabel('Mois')
    axes[1].set_ylabel('CA (DT)')
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.suptitle('')
    plt.tight_layout()
    plt.savefig(f'{save_dir}/eda_saisonnalite.png', dpi=100)
    plt.close()
    print(f'  -> Graphe sauvegarde : {save_dir}/eda_saisonnalite.png')

    print(f'\n[eda] Saisonnalite :')
    print(f'  Mois les plus forts  : {mois_forts}')
    print(f'  Mois les plus faibles: {mois_faibles}')
    print(f'  Amplitude            : {stats["amplitude_saisonniere"]:,.0f} DT')

    # ── 4. CA annuel ───────────────────────────────────────────
    ca_annuel = ts.groupby(ts.index.year).sum()
    ca_annuel_complet = ca_annuel[ca_annuel.index < 2026]

    years = list(ca_annuel_complet.index)
    cas   = list(ca_annuel_complet.values)
    croiss_tot = (cas[-1] - cas[0]) / cas[0] * 100
    stats['ca_annuel']         = dict(ca_annuel_complet)
    stats['croissance_totale'] = float(croiss_tot)

    print(f'\n[eda] CA Annuel :')
    for year, ca in ca_annuel_complet.items():
        print(f'  {year} : {ca:>15,.0f} DT')
    print(f'  Croissance totale 2022->2025 : +{croiss_tot:.1f}%')

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(ca_annuel_complet.index.astype(str),
           ca_annuel_complet.values, color='steelblue')
    for i, (year, ca) in enumerate(ca_annuel_complet.items()):
        ax.text(i, ca + ca_annuel_complet.max() * 0.01,
                f'{ca:,.0f}', ha='center', fontsize=9)
    ax.set_title('CA Annuel SAGAP (annees completes 2022-2025)')
    ax.set_ylabel('CA (DT)')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.tight_layout()
    plt.savefig(f'{save_dir}/eda_ca_annuel.png', dpi=100)
    plt.close()
    print(f'  -> Graphe sauvegarde : {save_dir}/eda_ca_annuel.png')

    return stats


if __name__ == '__main__':
    from data_loader import load_time_series
    ts = load_time_series()
    stats = run_eda(ts)
