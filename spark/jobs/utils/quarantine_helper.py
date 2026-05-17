"""
utils/quarantine_helper.py
──────────────────────────
Helper partagé pour la gestion des rejets GX et l'écriture en quarantine.
Élimine le copy-paste de _get_rejected_df + boucle dans chaque pipeline.
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from utils.silver_writer import write_silver


def get_rejected_df(df_clean: DataFrame, res: dict):
    """
    Retourne le sous-DataFrame des lignes qui échouent à une règle GX,
    avec une colonne `rejection_reason` expliquant le motif.
    Retourne None si la règle n'est pas applicable ou n'a aucun raté.
    """
    expectation = res["expectation_config"].type
    column      = res["expectation_config"].kwargs.get("column", "N/A")
    if column == "N/A":
        return None

    if expectation == "expect_column_values_to_match_regex":
        regex = res["expectation_config"].kwargs.get("regex", "")
        if not regex:
            return None
        df_rej = df_clean.filter(F.col(column).isNotNull() & ~F.col(column).rlike(regex))
        reason = F.lit(f"{column} invalide — ne correspond pas au regex attendu")

    elif expectation == "expect_column_values_to_not_be_null":
        df_rej = df_clean.filter(F.col(column).isNull())
        reason = F.lit(f"{column} invalide — valeur NULL non autorisée")

    elif expectation == "expect_column_values_to_be_in_set":
        value_set = res["expectation_config"].kwargs.get("value_set", [])
        df_rej = df_clean.filter(~F.col(column).isin(value_set))
        reason = F.lit(f"{column} invalide — valeur hors ensemble autorisé {value_set}")

    else:
        unexpected_values = res["result"].get("unexpected_list", [])
        if not unexpected_values:
            return None
        df_rej = df_clean.filter(F.col(column).isin(unexpected_values))
        reason = F.lit(f"{column} invalide — {expectation}")

    return df_rej.withColumn("rejection_reason", reason)


def process_rejections(
    df_clean: DataFrame,
    results: dict,
    quarantine_table: str,
    pk_col: str = "Id",
) -> set:
    """
    Parcourt les résultats GX, écrit les lignes rejetées en quarantine,
    et retourne l'ensemble des PKs rejetées.

    Paramètres
    ----------
    df_clean        : DataFrame après transformation (doit être mis en cache avant l'appel)
    results         : dict retourné par run_ge_validation
    quarantine_table: nom de la table quarantine cible
    pk_col          : colonne clé primaire à collecter (défaut : "Id")
    """
    rejected_pks = set()

    for res in results["results"]:
        if res["success"]:
            continue
        failed = res["result"].get("unexpected_count", 0)
        if not failed:
            continue

        df_rejected = get_rejected_df(df_clean, res)
        if df_rejected is None:
            continue

        count = df_rejected.count()
        if count > 0:
            write_silver(df_rejected, quarantine_table)
            print(f"⚠️  {count} lignes rejetées → {quarantine_table}")
            bad_pks = [row[pk_col] for row in df_rejected.select(pk_col).collect()]
            rejected_pks.update(bad_pks)

    return rejected_pks


def write_valid_or_all(
    df_clean: DataFrame,
    rejected_pks: set,
    silver_table: str,
    n_clean: int,
    pk_col: str = "Id",
):
    """
    Écrit en Silver les lignes valides (ou toutes si aucun rejet).
    `n_clean` est passé en paramètre pour éviter un .count() supplémentaire.
    """
    if rejected_pks:
        df_valid = df_clean.filter(~F.col(pk_col).isin(list(rejected_pks)))
        print(f"💾 Écriture Silver ({n_clean - len(rejected_pks)} lignes valides)...")
        write_silver(df_valid, silver_table)
    else:
        print(f"💾 Écriture Silver ({n_clean} lignes)...")
        write_silver(df_clean, silver_table)
