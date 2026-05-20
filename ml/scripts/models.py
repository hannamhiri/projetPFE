# =============================================================
# models.py — HW + SARIMA + Prophet + MLflow
# Logique : HW vs Prophet (add/mul) → gagnant vs SARIMA
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

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment(MLFLOW_EXPERIMENT)


def evaluate_ts(name, y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mae   = mean_absolute_error(y_true, y_pred)
    rmse  = np.sqrt(mean_squared_error(y_true, y_pred))
    mape  = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    smape = np.mean(2*np.abs(y_true-y_pred)/(np.abs(y_true)+np.abs(y_pred))) * 100
    bias  = np.mean(y_pred - y_true)
    return {'name':name,'pred':y_pred,
            'MAE':mae,'RMSE':rmse,'MAPE':mape,'SMAPE':smape,'Biais':bias}


def check_overfitting(name, ts_train, ts_test, pred_train, pred_test):
    mape_tr = np.mean(np.abs((ts_train.values - pred_train) / ts_train.values)) * 100
    mape_te = np.mean(np.abs((ts_test.values  - pred_test)  / ts_test.values))  * 100
    ecart   = abs(mape_tr - mape_te)
    status  = 'Pas d overfitting' if ecart < 2 else 'Legere tendance' if ecart < 5 else 'Overfitting'
    print(f'  Overfitting : train={mape_tr:.2f}% | test={mape_te:.2f}% | ecart={ecart:.2f}% -> {status}')
    return {'mape_train':mape_tr,'mape_test':mape_te,'ecart':ecart,'status':status}


def _log_mlflow(name, res, ovf, params):
    with mlflow.start_run(run_name=name):
        for k, v in params.items():
            mlflow.log_param(k, v)
        mlflow.log_metric('MAE',        res['MAE'])
        mlflow.log_metric('RMSE',       res['RMSE'])
        mlflow.log_metric('MAPE',       res['MAPE'])
        mlflow.log_metric('SMAPE',      res['SMAPE'])
        mlflow.log_metric('Biais',      abs(res['Biais']))
        mlflow.log_metric('mape_train', ovf['mape_train'])
        mlflow.log_metric('ovf_ecart',  ovf['ecart'])
        mlflow.set_tag('overfitting',   ovf['status'])
    print(f'  -> MLflow [{name}] enregistre')


# ── HW Additif ────────────────────────────────────────────────
def train_hw_additif(ts_train, ts_test, n_test):
    print('\n[models] HW Additif')
    model = ExponentialSmoothing(
        ts_train, trend='add', seasonal='add', seasonal_periods=SEASONAL_PERIODS
    ).fit(optimized=True)
    pred = model.forecast(n_test).values
    res  = evaluate_ts('HW-Add', ts_test.values, pred)
    ovf  = check_overfitting('HW-Add', ts_train, ts_test, model.fittedvalues.values, pred)
    _log_mlflow('HW-Add', res, ovf, {'model':'HW-Add','seasonal':'add','m':SEASONAL_PERIODS})
    print(f'  MAPE={res["MAPE"]:.2f}% | MAE={res["MAE"]:,.0f}')
    res['model_obj'] = model
    return res


# ── HW Multiplicatif ──────────────────────────────────────────
def train_hw_multiplicatif(ts_train, ts_test, n_test):
    print('\n[models] HW Multiplicatif')
    model = ExponentialSmoothing(
        ts_train, trend='add', seasonal='mul', seasonal_periods=SEASONAL_PERIODS
    ).fit(optimized=True)
    pred = model.forecast(n_test).values
    res  = evaluate_ts('HW-Mul', ts_test.values, pred)
    ovf  = check_overfitting('HW-Mul', ts_train, ts_test, model.fittedvalues.values, pred)
    _log_mlflow('HW-Mul', res, ovf, {'model':'HW-Mul','seasonal':'mul','m':SEASONAL_PERIODS})
    print(f'  MAPE={res["MAPE"]:.2f}% | MAE={res["MAE"]:,.0f}')
    res['model_obj'] = model
    return res


# ── Prophet Additif ───────────────────────────────────────────
def train_prophet_additif(ts_train, ts_test, n_test):
    print('\n[models] Prophet Additif')
    df_train = pd.DataFrame({'ds': ts_train.index, 'y': ts_train.values})
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                    daily_seasonality=False, seasonality_mode='additive')
    model.fit(df_train)
    fc   = model.predict(model.make_future_dataframe(periods=n_test, freq='MS'))
    pred = fc['yhat'].iloc[-n_test:].values
    res  = evaluate_ts('Prophet-Add', ts_test.values, pred)
    ovf  = check_overfitting('Prophet-Add', ts_train, ts_test,
                              model.predict(df_train)['yhat'].values, pred)
    _log_mlflow('Prophet-Add', res, ovf, {'model':'Prophet','mode':'additive'})
    print(f'  MAPE={res["MAPE"]:.2f}% | MAE={res["MAE"]:,.0f}')
    res['model_obj'] = model
    res['ci_low']    = fc['yhat_lower'].iloc[-n_test:].values
    res['ci_high']   = fc['yhat_upper'].iloc[-n_test:].values
    return res


# ── Prophet Multiplicatif ─────────────────────────────────────
def train_prophet_multiplicatif(ts_train, ts_test, n_test):
    print('\n[models] Prophet Multiplicatif')
    df_train = pd.DataFrame({'ds': ts_train.index, 'y': ts_train.values})
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                    daily_seasonality=False, seasonality_mode='multiplicative')
    model.fit(df_train)
    fc   = model.predict(model.make_future_dataframe(periods=n_test, freq='MS'))
    pred = fc['yhat'].iloc[-n_test:].values
    res  = evaluate_ts('Prophet-Mul', ts_test.values, pred)
    ovf  = check_overfitting('Prophet-Mul', ts_train, ts_test,
                              model.predict(df_train)['yhat'].values, pred)
    _log_mlflow('Prophet-Mul', res, ovf, {'model':'Prophet','mode':'multiplicative'})
    print(f'  MAPE={res["MAPE"]:.2f}% | MAE={res["MAE"]:,.0f}')
    res['model_obj'] = model
    res['ci_low']    = fc['yhat_lower'].iloc[-n_test:].values
    res['ci_high']   = fc['yhat_upper'].iloc[-n_test:].values
    return res


# ── SARIMA (toujours additif) ─────────────────────────────────
def train_sarima(ts_train, ts_test, n_test):
    print('\n[models] SARIMA Grid Search')
    best_aic, best_order, best_sarima = np.inf, None, None
    for p, d, q in itertools.product(SARIMA_P_RANGE, SARIMA_D_RANGE, SARIMA_Q_RANGE):
        try:
            m = SARIMAX(ts_train, order=(p,d,q),
                        seasonal_order=SARIMA_SEASONAL,
                        enforce_stationarity=False,
                        enforce_invertibility=False).fit(disp=False)
            if m.aic < best_aic:
                best_aic   = m.aic
                best_order = (p,d,q)
                best_sarima = m
        except: continue
    print(f'  Meilleur : SARIMA{best_order} | AIC={best_aic:.2f}')
    pred = best_sarima.forecast(steps=n_test).values
    name = f'SARIMA{best_order}'
    res  = evaluate_ts(name, ts_test.values, pred)
    ovf  = check_overfitting(name, ts_train, ts_test,
                              best_sarima.fittedvalues.values, pred)
    P, D, Q, m = SARIMA_SEASONAL
    _log_mlflow(name, res, ovf, {'model':'SARIMA','p':best_order[0],'d':1,
                                  'q':best_order[2],'P':P,'D':D,'Q':Q,'m':m})
    print(f'  MAPE={res["MAPE"]:.2f}% | MAE={res["MAE"]:,.0f}')
    res['model_obj']  = best_sarima
    res['best_order'] = best_order
    res['best_seas']  = SARIMA_SEASONAL
    return res


# ── Logique principale : HW vs Prophet → gagnant vs SARIMA ───
def run_h1_modeling(ts_train, ts_test, n_test):
    """
    Etape 1 : HW-Add vs HW-Mul
    Etape 2 : Prophet-Add vs Prophet-Mul
    Etape 3 : Meilleur (HW ou Prophet) vs SARIMA
    """
    print('\n=== H1 ETAPE 1 : HW Add vs Mul ===')
    res_hw_add = train_hw_additif(ts_train, ts_test, n_test)
    res_hw_mul = train_hw_multiplicatif(ts_train, ts_test, n_test)
    hw_best = res_hw_mul if res_hw_mul['MAPE'] < res_hw_add['MAPE'] else res_hw_add
    print(f'  HW gagnant : {hw_best["name"]} (MAPE={hw_best["MAPE"]:.2f}%)')

    print('\n=== H1 ETAPE 2 : Prophet Add vs Mul ===')
    res_pr_add = train_prophet_additif(ts_train, ts_test, n_test)
    res_pr_mul = train_prophet_multiplicatif(ts_train, ts_test, n_test)
    pr_best = res_pr_mul if res_pr_mul['MAPE'] < res_pr_add['MAPE'] else res_pr_add
    print(f'  Prophet gagnant : {pr_best["name"]} (MAPE={pr_best["MAPE"]:.2f}%)')

    # Gagnant HW vs Prophet
    hw_pr_best = hw_best if hw_best['MAPE'] < pr_best['MAPE'] else pr_best
    print(f'\n  Gagnant HW vs Prophet : {hw_pr_best["name"]} (MAPE={hw_pr_best["MAPE"]:.2f}%)')

    print('\n=== H1 ETAPE 3 : Gagnant vs SARIMA ===')
    res_sarima = train_sarima(ts_train, ts_test, n_test)

    if hw_pr_best['MAPE'] < res_sarima['MAPE']:
        print(f'  -> {hw_pr_best["name"]} gagne sur SARIMA')
    else:
        print(f'  -> SARIMA gagne sur {hw_pr_best["name"]}')

    return {
        'hw_add':    res_hw_add,
        'hw_mul':    res_hw_mul,
        'hw_best':   hw_best,
        'pr_add':    res_pr_add,
        'pr_mul':    res_pr_mul,
        'pr_best':   pr_best,
        'sarima':    res_sarima,
        'all':       [res_hw_add, res_hw_mul, res_pr_add, res_pr_mul, res_sarima]
    }


def select_best(all_results):
    best = min(all_results, key=lambda r: r['MAPE'])
    print(f'\n[models] Meilleur : {best["name"]} (MAPE={best["MAPE"]:.2f}%)')
    return best


if __name__ == '__main__':
    from data_loader import load_time_series
    from config import N_TEST
    ts       = load_time_series()
    ts_train = ts.iloc[:-N_TEST]
    ts_test  = ts.iloc[-N_TEST:]
    h1 = run_h1_modeling(ts_train, ts_test, N_TEST)
    best = select_best(h1['all'])