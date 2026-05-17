import great_expectations as gx
from great_expectations.core.validation_definition import ValidationDefinition
from great_expectations.checkpoint import Checkpoint
import logging

logger = logging.getLogger(__name__)


def run_ge_validation(df_spark, suite_name: str, get_suite_fn, asset_name: str):
    """
    Validation GX avec backend Pandas — fiable et compatible avec toutes les expectations.
    Le DataFrame Spark doit être mis en cache AVANT l'appel (fait dans chaque pipeline).
    toPandas() bénéficie donc du cache Spark déjà chaud (pas de re-lecture JDBC).
    """
    context = gx.get_context(mode="ephemeral")
    suite   = get_suite_fn(context, suite_name)

    # Conversion Pandas — rapide grâce au cache Spark déjà chaud
    df_pandas = df_spark.toPandas()

    # ── Datasource Pandas ─────────────────────────────────────────────────────
    try:
        datasource = context.data_sources.add_pandas(name=asset_name)
    except Exception:
        datasource = context.data_sources.get(asset_name)

    # ── Data asset ────────────────────────────────────────────────────────────
    try:
        data_asset = datasource.add_dataframe_asset(name=asset_name)
    except Exception:
        data_asset = datasource.get_asset(asset_name)

    # ── Batch definition ──────────────────────────────────────────────────────
    try:
        batch_def = data_asset.add_batch_definition_whole_dataframe(f"{asset_name}_batch")
    except ValueError:
        batch_def = data_asset.get_batch_definition(f"{asset_name}_batch")

    # ── Validation Definition ─────────────────────────────────────────────────
    validation_def_name = f"{asset_name}_validation"
    try:
        validation_definition = ValidationDefinition(
            name=validation_def_name,
            data=batch_def,
            suite=suite,
        )
        validation_definition = context.validation_definitions.add(validation_definition)
    except Exception:
        validation_definition = context.validation_definitions.get(validation_def_name)

    # ── Checkpoint ────────────────────────────────────────────────────────────
    checkpoint_name = f"{asset_name}_checkpoint"
    try:
        checkpoint = context.checkpoints.add(
            Checkpoint(
                name=checkpoint_name,
                validation_definitions=[validation_definition],
            )
        )
    except Exception:
        checkpoint = context.checkpoints.get(checkpoint_name)

    # ── Lancer la validation ──────────────────────────────────────────────────
    checkpoint_result = checkpoint.run(
        batch_parameters={"dataframe": df_pandas},
    )

    # ── Extraire le résultat ──────────────────────────────────────────────────
    validation_result = list(checkpoint_result.run_results.values())[0]

    if validation_result["success"]:
        print(f"✅ Validation GX OK pour {asset_name}")
    else:
        print(f"\n❌ Validation GX — anomalies détectées pour {asset_name} :")
        print(f"{'─' * 50}")
        for result in validation_result["results"]:
            if not result["success"]:
                expectation_type   = result["expectation_config"].type
                column             = result["expectation_config"].kwargs.get("column", "table-level")
                unexpected_count   = result["result"].get("unexpected_count", "?")
                unexpected_percent = result["result"].get("unexpected_percent", "?")
                element_count      = result["result"].get("element_count", "?")

                percent_str = f"{unexpected_percent:.4f}%" if isinstance(unexpected_percent, float) else "?"
                print(f"\n  Règle    : {expectation_type}")
                print(f"  Colonne  : {column}")
                print(f"  Total    : {element_count} lignes")
                print(f"  Échoués  : {unexpected_count} lignes ({percent_str})")

        print(f"{'─' * 50}")
        print(f"⚠️  Traitement des anomalies en cours ...")

    return validation_result