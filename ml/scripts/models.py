# =============================================================
# models.py — HW + SARIMA + Prophet + MLflow + Model Registry
# Logique : HW vs Prophet (add/mul) → gagnant vs SARIMA
# =============================================================

import os, pandas as pd, numpy as np, itertools
import mlflow, warnings
import mlflow
import mlflow.pyfunc
import mlflow.statsmodels  
warnings.filterwarnings('ignore')

from mlflow.tracking import MlflowClient
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

REGISTRY_NAME = 'TimeSeries_SalesForcast'


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


# ── Custom MLflow Model Wrapper ────────────────────────────────
class ProphetWrapper(mlflow.pyfunc.PythonModel):
    """Wrapper Prophet pour MLflow Model Registry"""
    def __init__(self, model):
        self.model = model

    def predict(self, context, model_input):
        future = self.model.make_future_dataframe(
            periods=len(model_input), freq='MS'
        )
        fc = self.model.predict(future)
        return fc['yhat'].iloc[-len(model_input):].values


def register_best_model(best):
    print(f'\n[registry] Enregistrement du modele {best["name"]}...')

    if float(best['MAPE']) >= MAPE_BON:
        print(f'  MAPE={best["MAPE"]:.2f}% >= {MAPE_BON}%')
        print(f'  -> Modele non eligible pour le Registry')
        return None

    # ── imports au niveau module (pas dans la fonction) ────────
    import mlflow.pyfunc
    import mlflow.statsmodels

    client = MlflowClient()

    try:
        with mlflow.start_run(run_name=f'Registry_{best["name"]}'):
            mlflow.log_metric('MAPE_final', best['MAPE'])
            mlflow.log_metric('MAE_final',  best['MAE'])
            mlflow.log_param('model_name',  best['name'])
            mlflow.log_param('eligible',    True)

            if 'Prophet' in best['name']:
                wrapper = ProphetWrapper(best['model_obj'])
                mlflow.pyfunc.log_model(
                    artifact_path='model',
                    python_model=wrapper,
                    registered_model_name=REGISTRY_NAME
                )
                print(f'  -> Prophet enregistre via pyfunc wrapper')

            elif 'HW' in best['name']:
                mlflow.statsmodels.log_model(
                    statsmodels_model=best['model_obj'],
                    artifact_path='model',
                    registered_model_name=REGISTRY_NAME
                )
                print(f'  -> HW enregistre dans le Registry')

            elif 'SARIMA' in best['name']:
                mlflow.statsmodels.log_model(
                    statsmodels_model=best['model_obj'],
                    artifact_path='model',
                    registered_model_name=REGISTRY_NAME
                )
                print(f'  -> SARIMA enregistre dans le Registry')

        # reste du code inchangé...

        # Recuperer la derniere version
        versions = client.get_latest_versions(REGISTRY_NAME)
        if not versions:
            print(f'  -> Aucune version trouvee')
            return None

        latest = max(versions, key=lambda v: int(v.version))

        # Archiver les anciennes versions Production
        for v in versions:
            if v.current_stage == 'Production' and v.version != latest.version:
                client.transition_model_version_stage(
                    name=REGISTRY_NAME, version=v.version, stage='Archived'
                )
                print(f'  -> Version {v.version} archivee')

        # Promouvoir en Production
        client.transition_model_version_stage(
            name=REGISTRY_NAME, version=latest.version, stage='Production'
        )
        print(f'  -> Version {latest.version} promue en Production')
        print(f'  -> Registry : {REGISTRY_NAME} v{latest.version} [Production]')
        return latest.version

    except Exception as e:
        print(f'  -> Erreur Registry : {e}')
        return None


def run_ab_testing(ts, all_results):
    """
    Comparer nouveau meilleur modele vs Production
    Promouvoir si amelioration > 5%
    """
    print(f'\n[ab_testing] Comparaison nouveau vs Production...')
    client   = MlflowClient()
    new_best = min(all_results, key=lambda r: r['MAPE'])
    mape_new = float(new_best['MAPE'])

    try:
        # Verifier si registry existe
        registered_models = [rm.name for rm in client.search_registered_models()]
        if REGISTRY_NAME not in registered_models:
            print(f'  -> Registry vide — premier deploiement')
            register_best_model(new_best)
            return new_best['name']

        versions_prod = client.get_latest_versions(
            REGISTRY_NAME, stages=['Production']
        )

        if not versions_prod:
            print(f'  -> Pas de modele en Production')
            print(f'  -> Premier deploiement direct')
            register_best_model(new_best)
            return new_best['name']

        # MAPE du modele en production
        prod_version = versions_prod[0]
        prod_run     = client.get_run(prod_version.run_id)
        mape_prod    = float(prod_run.data.metrics.get('MAPE_final', 999))

        print(f'  Modele Production actuel : MAPE = {mape_prod:.2f}%')
        print(f'  Nouveau modele           : {new_best["name"]} MAPE = {mape_new:.2f}%')

        amelioration = (mape_prod - mape_new) / mape_prod * 100

        with mlflow.start_run(run_name='AB_Testing'):
            mlflow.log_metric('mape_production',  mape_prod)
            mlflow.log_metric('mape_nouveau',      mape_new)
            mlflow.log_metric('amelioration_pct',  amelioration)

            mlflow.log_param('modele_production', prod_version.name)
            mlflow.log_param('modele_nouveau',    new_best['name'])
            mlflow.log_param('version_production', prod_version.version)
            if mape_new < mape_prod * 0.95:
                print(f'  -> Amelioration {amelioration:.1f}% > 5% -> deployer nouveau')
                mlflow.log_param('decision', 'DEPLOY_NEW')
                mlflow.log_param('winner',   new_best['name'])
                register_best_model(new_best)
                winner = new_best['name']
            else:
                print(f'  -> Amelioration {amelioration:.1f}% < 5% -> garder Production')
                mlflow.log_param('decision', 'KEEP_PRODUCTION')
                mlflow.log_param('winner',   'Production')
                winner = 'Production'

        return winner

    except Exception as e:
        print(f'  -> Erreur A/B Testing : {e}')
        print(f'  -> Deploiement direct du nouveau modele')
        register_best_model(new_best)
        return new_best['name']


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


# ── SARIMA ────────────────────────────────────────────────────
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
                best_aic, best_order, best_sarima = m.aic, (p,d,q), m
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


# ── Logique H1 : HW vs Prophet → gagnant vs SARIMA ───────────
def run_h1_modeling(ts_train, ts_test, n_test):
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

    hw_pr_best = hw_best if hw_best['MAPE'] < pr_best['MAPE'] else pr_best
    print(f'\n  Gagnant HW vs Prophet : {hw_pr_best["name"]} (MAPE={hw_pr_best["MAPE"]:.2f}%)')

    print('\n=== H1 ETAPE 3 : Gagnant vs SARIMA ===')
    res_sarima = train_sarima(ts_train, ts_test, n_test)

    if hw_pr_best['MAPE'] < res_sarima['MAPE']:
        print(f'  -> {hw_pr_best["name"]} gagne sur SARIMA')
    else:
        print(f'  -> SARIMA gagne sur {hw_pr_best["name"]}')

    return {
        'hw_add':  res_hw_add, 'hw_mul':  res_hw_mul, 'hw_best': hw_best,
        'pr_add':  res_pr_add, 'pr_mul':  res_pr_mul, 'pr_best': pr_best,
        'sarima':  res_sarima,
        'all':     [res_hw_add, res_hw_mul, res_pr_add, res_pr_mul, res_sarima]
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
    h1   = run_h1_modeling(ts_train, ts_test, N_TEST)
    best = select_best(h1['all'])
    run_ab_testing(ts, h1['all'])