# dagster/pipeline.py
import os, time, smtplib, requests, subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dagster import (
    asset, schedule, define_asset_job,
    AssetSelection, AssetKey, Definitions,
    run_status_sensor, RunStatusSensorContext,
    DagsterRunStatus,
)
from dagster_dbt import DbtCliResource, DbtProject, DagsterDbtTranslator, dbt_assets

# -- Config -------------------------------------------------------------------
AIRBYTE_URL           = os.getenv("AIRBYTE_URL",           "http://host.docker.internal:8000")
AIRBYTE_CONN_ID       = os.getenv("AIRBYTE_CONNECTION_ID", "012ac2da-0a87-4781-8930-2f3fa69063c5")
AIRBYTE_CLIENT_ID     = os.getenv("AIRBYTE_CLIENT_ID",     "2118c7f2-94f7-46fa-a2a0-71e044c8badd")
AIRBYTE_CLIENT_SECRET = os.getenv("AIRBYTE_CLIENT_SECRET", "Lwz1MWLeoMXNtrPHK95Rj5u92abORNC4")
DBT_PROJECT_DIR  = os.getenv("DBT_PROJECT_DIR",  "/dbt")
DBT_PROFILES_DIR = os.getenv("DBT_PROFILES_DIR", "/dbt")
SILVER_TABLES = [
    "client","document","documentline","documentstatus","documenttype",
    "item","family","geographicalarea","productitem","warehouse",
]
CLICKHOUSE_HOST     = os.getenv("CLICKHOUSE_HOST",      "localhost")
CLICKHOUSE_PORT     = int(os.getenv("CLICKHOUSE_PORT",  "8123"))
CLICKHOUSE_DB       = os.getenv("CLICKHOUSE_SILVER_DB", "silver")
CLICKHOUSE_USER     = os.getenv("CLICKHOUSE_USER",      "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD",  "")
CUBEJS_URL        = os.getenv("CUBEJS_URL",        "http://cubejs:4000")
CUBEJS_API_SECRET = os.getenv("CUBEJS_API_SECRET", "sagap_cube_secret_2024_pfe_decisonnel_open_source")
SMTP_HOST     = os.getenv("DAGSTER_SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("DAGSTER_SMTP_PORT", "587"))
SMTP_USER     = os.getenv("DAGSTER_SMTP_USER",     "")
SMTP_PASSWORD = os.getenv("DAGSTER_SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("DAGSTER_EMAIL_FROM",    "")
EMAIL_TO      = os.getenv("DAGSTER_EMAIL_TO",      "")

# -- ML Config ----------------------------------------------------------------
ML_PIPELINE_SCRIPT = os.getenv("ML_PIPELINE_SCRIPT", "/app/scripts/pipeline.py")

# -- dbt ----------------------------------------------------------------------
dbt_project  = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_resource = DbtCliResource(project_dir=DBT_PROJECT_DIR, profiles_dir=DBT_PROFILES_DIR, target="dev")

# -- Translator ---------------------------------------------------------------
class SagapDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props):
        if dbt_resource_props.get("resource_type") == "source":
            return AssetKey(["silver", dbt_resource_props.get("name", "unknown")])
        return super().get_asset_key(dbt_resource_props)
    def get_group_name(self, dbt_resource_props):
        if dbt_resource_props.get("resource_type") == "source":
            return "silver"
        return super().get_group_name(dbt_resource_props)

@dbt_assets(manifest=dbt_project.manifest_path, dagster_dbt_translator=SagapDbtTranslator())
def dbt_models(context, dbt: DbtCliResource):
    yield from dbt.cli(["run"], context=context).stream()

# -- Email --------------------------------------------------------------------
def send_email(subject, body):
    if not SMTP_USER or not EMAIL_TO:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
    except Exception as e:
        print("Email error: " + str(e))

# -- Sensors ------------------------------------------------------------------
@run_status_sensor(run_status=DagsterRunStatus.SUCCESS)
def email_on_pipeline_success(context: RunStatusSensorContext):
    job_name = context.dagster_run.job_name
    if job_name not in ("full_pipeline", "dbt_gold_refresh", "ml_timeseries_job"):
        return
    send_email(
        "[OK] Pipeline " + job_name + " reussi",
        "Bonjour,\n\nLe pipeline '" + job_name + "' s'est termine avec succes.\n\nRun ID : " + context.dagster_run.run_id + "\n\nCordialement,\nHana Data Platform"
    )

@run_status_sensor(run_status=DagsterRunStatus.FAILURE)
def email_on_pipeline_failure(context: RunStatusSensorContext):
    job_name = context.dagster_run.job_name
    if job_name not in ("full_pipeline", "dbt_gold_refresh", "ml_timeseries_job"):
        return
    send_email(
        "[ERREUR] Pipeline " + job_name + " echoue",
        "Bonjour,\n\nLe pipeline '" + job_name + "' a echoue.\n\nRun ID : " + context.dagster_run.run_id + "\n\nVerifiez les logs Dagster.\n\nCordialement,\nHana Data Platform"
    )

# -- Airbyte ------------------------------------------------------------------
def _get_airbyte_token(context):
    r = requests.post(
        AIRBYTE_URL + "/api/v1/applications/token",
        json={"client_id": AIRBYTE_CLIENT_ID, "client_secret": AIRBYTE_CLIENT_SECRET},
        headers={"Content-Type": "application/json"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

# -- ASSETS -------------------------------------------------------------------

# 1. BRONZE
@asset(group_name="bronze", description="Sync Airbyte SAGAP -> Bronze")
def airbyte_sync(context):
    token = _get_airbyte_token(context)
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
    trigger = requests.post(
        AIRBYTE_URL + "/api/public/v1/jobs",
        json={"connectionId": AIRBYTE_CONN_ID, "jobType": "sync"},
        headers=headers, timeout=30)
    if trigger.status_code == 409:
        r = requests.get(
            AIRBYTE_URL + "/api/public/v1/jobs",
            params={"connectionId": AIRBYTE_CONN_ID, "jobType": "sync", "limit": 1},
            headers=headers, timeout=30)
        r.raise_for_status()
        job_id = r.json()["data"][0]["jobId"]
    else:
        trigger.raise_for_status()
        job_id = trigger.json()["jobId"]
    context.log.info("Airbyte job_id=" + str(job_id))
    for attempt in range(360):
        time.sleep(10)
        if attempt % 50 == 0 and attempt > 0:
            token = _get_airbyte_token(context)
            headers["Authorization"] = "Bearer " + token
        status = requests.get(
            AIRBYTE_URL + "/api/public/v1/jobs/" + str(job_id),
            headers=headers, timeout=30).json()["status"]
        context.log.info("[" + str(attempt+1) + "] status=" + status)
        if status == "succeeded":
            return {"job_id": job_id, "status": "succeeded"}
        if status in ("failed", "cancelled", "incomplete"):
            raise Exception("Airbyte job " + status)
    raise Exception("Timeout Airbyte 60min")

# 2. SILVER - Spark
@asset(group_name="silver", deps=[airbyte_sync], description="Nettoyage PySpark Bronze -> Silver")
def spark_silver_cleaning(context):
    import docker
    client    = docker.from_env()
    container = client.containers.get("spark_clean")

    # Créer l'exec
    exec_id = client.api.exec_create(
        container.id,
        cmd=["python3", "/opt/jobs/main_clean_silver.py"],
        stdout=True, stderr=True
    )

    # Lancer et streamer les logs
    for chunk in client.api.exec_start(exec_id["Id"], stream=True):
        if chunk:
            line = chunk.decode("utf-8", errors="replace").strip()
            if line:
                context.log.info(line)

    # Attendre que l'exec soit vraiment terminé
    import time
    for _ in range(60):
        inspect = client.api.exec_inspect(exec_id["Id"])
        if not inspect.get("Running", True):
            break
        time.sleep(2)

    exit_code = client.api.exec_inspect(exec_id["Id"]).get("ExitCode")

    if exit_code is None:
        context.log.warning("exit_code=None — on suppose succes")
        return {"status": "success"}

    if exit_code != 0:
        raise Exception("Spark failed exit_code=" + str(exit_code))

    return {"status": "success"}

# 3. SILVER - Verification
@asset(group_name="silver", deps=[spark_silver_cleaning],
       description="Verifie que les 10 tables Silver sont pretes dans ClickHouse")
def silver_ready(context):
    import clickhouse_connect
    MAX_RETRIES, RETRY_DELAY = 30, 20
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
        database=CLICKHOUSE_DB, username=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD)
    for attempt in range(1, MAX_RETRIES + 1):
        missing, empty = [], []
        for table in SILVER_TABLES:
            try:
                count = client.query(
                    "SELECT count() FROM `" + CLICKHOUSE_DB + "`.`" + table + "` LIMIT 1"
                ).first_row[0]
                if count == 0:
                    empty.append(table)
                else:
                    context.log.info("OK " + table + " = " + str(count) + " lignes")
            except Exception as e:
                err = str(e).lower()
                if "doesn't exist" in err or "unknown table" in err:
                    missing.append(table)
                else:
                    raise
        if not missing and not empty:
            context.log.info("Toutes les tables Silver pretes.")
            return {"status": "ready"}
        context.log.warning("Manquantes=" + str(missing) + " Vides=" + str(empty))
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    raise Exception("Timeout Silver. Manquantes=" + str(missing) + " Vides=" + str(empty))

# 4. SILVER - Tables individuelles
def _make_silver_asset(table_name):
    @asset(
        name=table_name,
        key_prefix=["silver"],
        group_name="silver",
        deps=[silver_ready],
        description="Table ClickHouse silver." + table_name,
    )
    def _silver_asset(context):
        context.log.info("Table silver." + table_name + " disponible.")
        return {"table": table_name, "status": "ready"}
    return _silver_asset

silver_source_assets = [_make_silver_asset(t) for t in SILVER_TABLES]

# 5. GOLD - dbt docs
@asset(group_name="gold", deps=[dbt_models], description="Genere la documentation dbt")
def dbt_docs(context):
    result = subprocess.run(
        ["dbt", "docs", "generate",
         "--project-dir", DBT_PROJECT_DIR,
         "--profiles-dir", DBT_PROFILES_DIR,
         "--target", "dev"],
        capture_output=True, text=True, cwd=DBT_PROJECT_DIR)
    if result.returncode != 0:
        for line in result.stderr.splitlines():
            context.log.error(line)
        raise Exception("dbt docs generate failed")
    context.log.info("Docs dbt generes.")
    return {"status": "docs_generated"}

# 6. SEMANTIC - Cube.js
@asset(group_name="semantic", deps=[dbt_docs], description="Rafraichit Cube.js")
def cube_refresh(context):
    resp = requests.post(
        CUBEJS_URL + "/cubejs-api/v1/pre-aggregations/jobs",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + CUBEJS_API_SECRET},
        json={"action": "post", "selector": {"contexts": [{"securityContext": {}}]}},
        timeout=30)
    if resp.status_code not in (200, 201):
        context.log.warning("Cube.js " + str(resp.status_code) + " - pas bloquant")
    else:
        context.log.info("Cube.js rafraichi.")
    return {"status": "refreshed"}

# 7. SEMANTIC - Superset sync
@asset(group_name="semantic", deps=[cube_refresh],
       description="Synchronise les mesures Cube.js vers Superset")
def superset_sync(context):
    import docker
    client    = docker.from_env()
    container = client.containers.get("superset")
    exec_id   = client.api.exec_create(
        container.id,
        cmd=["python3", "/app/sync_cube_to_superset.py"],
        stdout=True, stderr=True)
    for chunk in client.api.exec_start(exec_id["Id"], stream=True):
        if chunk:
            line = chunk.decode("utf-8", errors="replace").strip()
            if line:
                context.log.info(line)
    exit_code = client.api.exec_inspect(exec_id["Id"]).get("ExitCode", -1)
    if exit_code != 0:
        raise Exception("superset_sync failed — exit_code=" + str(exit_code))
    context.log.info("Synchronisation Cube.js -> Superset terminee.")
    return {"status": "synced"}

# =============================================================
# 8. ML TIMESERIES — 1 seul asset qui appelle pipeline.py
#    Se positionne après gold (dbt_docs), en parallèle de semantic
# =============================================================
@asset(
    group_name="ml_timeseries",
    deps=[dbt_docs],
    description="[ML] Pipeline complet : EDA -> Decomposition -> HW + SARIMA + Prophet -> Prediction -> gold.ml_predictions"
)
def ml_timeseries_pipeline(context):
    import docker
    context.log.info("Lancement du pipeline ML dans ml_engine...")
    context.log.info("Script : " + ML_PIPELINE_SCRIPT)

    client    = docker.from_env()
    container = client.containers.get("ml_engine")
    exec_id   = client.api.exec_create(
        container.id,
        cmd=["python3", ML_PIPELINE_SCRIPT],
        stdout=True, stderr=True
    )
    for chunk in client.api.exec_start(exec_id["Id"], stream=True):
        if chunk:
            line = chunk.decode("utf-8", errors="replace").strip()
            if line:
                context.log.info(line)

    exit_code = client.api.exec_inspect(exec_id["Id"]).get("ExitCode", -1)
    if exit_code != 0:
        raise Exception("ML pipeline failed — exit_code=" + str(exit_code))

    context.log.info("Pipeline ML termine avec succes")
    context.log.info("Predictions disponibles dans gold.ml_predictions")
    context.log.info("Artifacts disponibles dans MLflow -> http://mlflow:5000")
    return {"status": "ml_pipeline_done"}

# -- Jobs ---------------------------------------------------------------------
_bronze        = AssetSelection.assets(airbyte_sync)
_silver        = AssetSelection.assets(spark_silver_cleaning) | AssetSelection.assets(silver_ready)
_silver_tables = AssetSelection.groups("silver") - _silver
_dbt           = AssetSelection.assets(dbt_models)
_docs          = AssetSelection.assets(dbt_docs)
_cube          = AssetSelection.assets(cube_refresh)
_superset      = AssetSelection.assets(superset_sync)
_ml            = AssetSelection.assets(ml_timeseries_pipeline)

full_pipeline_job = define_asset_job(
    name="full_pipeline",
    description="Pipeline complet : Bronze -> Silver -> Gold -> Semantic + ML",
    selection=_bronze | _silver | _silver_tables | _dbt | _docs | _cube | _superset | _ml,
    config={"execution": {"config": {"in_process": {}}}},
)

dbt_gold_refresh_job = define_asset_job(
    name="dbt_gold_refresh",
    description="Refresh dbt uniquement (18 modeles sagap)",
    selection=_dbt | _docs,
)

ml_timeseries_job = define_asset_job(
    name="ml_timeseries_job",
    description="Pipeline ML series temporelles — peut tourner independamment",
    selection=_ml,
)

@schedule(job=full_pipeline_job, cron_schedule="0 2 * * *")
def nightly_pipeline_schedule(context):
    return {}

@schedule(job=dbt_gold_refresh_job, cron_schedule="0 */6 * * *")
def dbt_refresh_schedule(context):
    return {}

@schedule(job=ml_timeseries_job, cron_schedule="0 3 1 * *")  # 1er de chaque mois a 3h
def monthly_ml_schedule(context):
    return {}

# -- Definitions --------------------------------------------------------------
defs = Definitions(
    assets=[
        airbyte_sync,
        spark_silver_cleaning,
        silver_ready,
        *silver_source_assets,
        dbt_models,
        dbt_docs,
        cube_refresh,
        superset_sync,
        ml_timeseries_pipeline,
    ],
    jobs=[full_pipeline_job, dbt_gold_refresh_job, ml_timeseries_job],
    schedules=[nightly_pipeline_schedule, dbt_refresh_schedule, monthly_ml_schedule],
    sensors=[email_on_pipeline_success, email_on_pipeline_failure],
    resources={"dbt": dbt_resource},
)