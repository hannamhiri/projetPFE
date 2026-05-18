# =============================================================
# models.py — Entraînement HW + SARIMA + Prophet + MLflow
# =============================================================

import pandas as pd
import numpy as np
import itertools
import mlflow
import warnings
warnings.filterwarnings('ignore')

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

from config import (
    MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT,
    SARIMA_P_RANGE, SARIMA_D_RANGE, SARIMA_Q_RANGE,
    SARIMA_SEASONAL, SEASONAL_PERIODS, MAPE_BON, MAPE_EXCELLENT
)


# ── MLflow setup ──────────────────────────────────────────────
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment(MLFLOW_EXPERIMENT)


def evaluate_ts(name: str, y_true, y_pred, ts_train=None) -> dict:
    """Calculer les métriques MAE, RMSE, MAPE, SMAPE, Biais."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mae   = mean_absolute_error(y_true, y_pred)
    rmse  = np.sqrt(mean_squared_error(y_true, y_pred))
    mape  = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    smape = np.mean(2 * np.abs(y_true - y_pred) /
                    (np.abs(y_true) + np.abs(y_pred))) * 100
    bias  = np.mean(y_pred - y_true)
    return {
        'name': name, 'pred': y_pred,
        'MAE': mae, 'RMSE': rmse,
        'MAPE': mape, 'SMAPE': smape, 'Biais': bias
    }


def check_overfitting(name: str, ts_train, ts_test, pred_train, pred_test):
    """Vérifier l'overfitting en comparant MAPE train vs test."""
    mape_tr = np.mean(np.abs((ts_train.values - pred_train) / ts_train.values)) * 100
    mape_te = np.mean(np.abs((ts_test.values  - pred_test)  / ts_test.values))  * 100
    ecart   = abs(mape_tr - mape_te)
    if ecart < 2:
        status = 'Pas d overfitting'
    elif ecart < 5:
        status = 'Legere tendance — acceptable'
    else:
        status = 'Overfitting detecte'
    print(f'  Overfitting : train={mape_tr:.2f}% | test={mape_te:.2f}% | ecart={ecart:.2f}% -> {status}')
    return {'mape_train': mape_tr, 'mape_test': mape_te, 'ecart': ecart, 'status': status}


def train_hw_additif(ts_train, ts_test, n_test: int) -> dict:
    """Entraîner Holt-Winters Additif."""
    print('\n[models] 1 — Holt-Winters Additif')

    model = ExponentialSmoothing(
        ts_train, trend='add', seasonal='add', seasonal_periods=SEASONAL_PERIODS
    ).fit(optimized=True)

    pred = model.forecast(n_test).values
    res  = evaluate_ts('HW-Additif', ts_test.values, pred)
    ovf  = check_overfitting('HW-Additif', ts_train, ts_test,
                              model.fittedvalues.values, pred)

    _log_mlflow('HW-Additif', res, ovf, {
        'model': 'HW-Additif', 'trend': 'add',
        'seasonal': 'add', 'seasonal_periods': SEASONAL_PERIODS,
        'n_train': len(ts_train), 'n_test': len(ts_test)
    })

    print(f'  MAE={res["MAE"]:,.0f} | RMSE={res["RMSE"]:,.0f} | MAPE={res["MAPE"]:.2f}%')
    res['model_obj'] = model
    return res


def train_hw_multiplicatif(ts_train, ts_test, n_test: int) -> dict:
    """Entraîner Holt-Winters Multiplicatif."""
    print('\n[models] 2 — Holt-Winters Multiplicatif')

    model = ExponentialSmoothing(
        ts_train, trend='add', seasonal='mul', seasonal_periods=SEASONAL_PERIODS
    ).fit(optimized=True)

    pred = model.forecast(n_test).values
    res  = evaluate_ts('HW-Multiplicatif', ts_test.values, pred)
    ovf  = check_overfitting('HW-Multiplicatif', ts_train, ts_test,
                              model.fittedvalues.values, pred)

    _log_mlflow('HW-Multiplicatif', res, ovf, {
        'model': 'HW-Multiplicatif', 'trend': 'add',
        'seasonal': 'mul', 'seasonal_periods': SEASONAL_PERIODS,
        'n_train': len(ts_train), 'n_test': len(ts_test)
    })

    print(f'  MAE={res["MAE"]:,.0f} | RMSE={res["RMSE"]:,.0f} | MAPE={res["MAPE"]:.2f}%')
    res['model_obj'] = model
    return res


def train_sarima(ts_train, ts_test, n_test: int) -> dict:
    """Grid search SARIMA avec saisonnalité fixée."""
    print('\n[models] 3 — SARIMA Grid Search')

    best_aic    = np.inf
    best_order  = None
    best_sarima = None
    results_grid = []

    for p, d, q in itertools.product(
        SARIMA_P_RANGE, SARIMA_D_RANGE, SARIMA_Q_RANGE
    ):
        try:
            m = SARIMAX(
                ts_train,
                order=(p, d, q),
                seasonal_order=SARIMA_SEASONAL,
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(disp=False)
            results_grid.append({
                'order': (p, d, q), 'AIC': m.aic,
                'BIC': m.bic, 'model': m
            })
            if m.aic < best_aic:
                best_aic    = m.aic
                best_order  = (p, d, q)
                best_sarima = m
        except Exception:
            continue

    print(f'  Meilleur : SARIMA{best_order}{SARIMA_SEASONAL} | AIC={best_aic:.2f}')

    pred       = best_sarima.forecast(steps=n_test).values
    name       = f'SARIMA{best_order}'
    res        = evaluate_ts(name, ts_test.values, pred)
    ovf        = check_overfitting(name, ts_train, ts_test,
                                   best_sarima.fittedvalues.values, pred)

    P, D, Q, m = SARIMA_SEASONAL
    _log_mlflow(name, res, ovf, {
        'model': 'SARIMA',
        'p': best_order[0], 'd': best_order[1], 'q': best_order[2],
        'P': P, 'D': D, 'Q': Q, 'm': m,
        'AIC': best_aic,
        'n_train': len(ts_train), 'n_test': len(ts_test)
    })

    print(f'  MAE={res["MAE"]:,.0f} | RMSE={res["RMSE"]:,.0f} | MAPE={res["MAPE"]:.2f}%')
    res['model_obj']  = best_sarima
    res['best_order'] = best_order
    res['best_seas']  = SARIMA_SEASONAL
    return res


def train_prophet(ts_train, ts_test, n_test: int) -> dict:
    """Entraîner Prophet."""
    print('\n[models] 4 — Prophet')

    df_train = pd.DataFrame({'ds': ts_train.index, 'y': ts_train.values})

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode='additive'
    )
    model.fit(df_train)

    future   = model.make_future_dataframe(periods=n_test, freq='MS')
    forecast = model.predict(future)
    pred     = forecast['yhat'].iloc[-n_test:].values

    res = evaluate_ts('Prophet', ts_test.values, pred)
    ovf = check_overfitting('Prophet', ts_train, ts_test,
                             model.predict(df_train)['yhat'].values, pred)

    _log_mlflow('Prophet', res, ovf, {
        'model': 'Prophet',
        'yearly_seasonality': True,
        'seasonality_mode': 'additive',
        'n_train': len(ts_train), 'n_test': len(ts_test)
    })

    print(f'  MAE={res["MAE"]:,.0f} | RMSE={res["RMSE"]:,.0f} | MAPE={res["MAPE"]:.2f}%')
    res['model_obj'] = model
    res['ci_low']    = forecast['yhat_lower'].iloc[-n_test:].values
    res['ci_high']   = forecast['yhat_upper'].iloc[-n_test:].values
    return res


def select_best(all_results: list) -> dict:
    """Sélectionner le meilleur modèle selon MAPE."""
    best = min(all_results, key=lambda r: r['MAPE'])
    print(f'\n[models] Meilleur modele : {best["name"]} (MAPE={best["MAPE"]:.2f}%)')
    return best


def _log_mlflow(name: str, res: dict, ovf: dict, params: dict):
    """Logger les métriques et paramètres dans MLflow."""
    with mlflow.start_run(run_name=name):
        for k, v in params.items():
            mlflow.log_param(k, v)
        mlflow.log_metric('MAE',         res['MAE'])
        mlflow.log_metric('RMSE',        res['RMSE'])
        mlflow.log_metric('MAPE',        res['MAPE'])
        mlflow.log_metric('SMAPE',       res['SMAPE'])
        mlflow.log_metric('Biais',       abs(res['Biais']))
        mlflow.log_metric('mape_train',  ovf['mape_train'])
        mlflow.log_metric('ovf_ecart',   ovf['ecart'])
        mlflow.set_tag('overfitting', ovf['status'])
    print(f'  -> MLflow run [{name}] enregistre')


if __name__ == '__main__':
    from data_loader import load_time_series
    from config import N_TEST

    ts       = load_time_series()
    ts_train = ts.iloc[:-N_TEST]
    ts_test  = ts.iloc[-N_TEST:]

    all_results = []
    all_results.append(train_hw_additif(ts_train, ts_test, N_TEST))
    all_results.append(train_hw_multiplicatif(ts_train, ts_test, N_TEST))
    all_results.append(train_sarima(ts_train, ts_test, N_TEST))
    all_results.append(train_prophet(ts_train, ts_test, N_TEST))

    best = select_best(all_results)
    print(f'\nBest : {best["name"]} MAPE={best["MAPE"]:.2f}%')
