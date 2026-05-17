from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.item_expectations import get_item_suite
from utils.silver_writer import write_silver

BRONZE_TABLE = '"bronze"."Item"'
SILVER_TABLE = "silver.Item"
USEFUL_COLS  = ["Id", "Code", "Label", "IdProductItem", "IdFamily"]
REGEX        = ".*[a-zA-Z0-9\u00C0-\u024F].*"

JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {
    "user": "warehouse",
    "password": "warehouse",
    "driver": "org.postgresql.Driver"
}


def extract(spark: SparkSession):
    """Pushdown SQL — filtre et projection côté PostgreSQL."""
    query = """
        (SELECT "Id", "Code", "Description", "IdProductItem", "IdFamily"
         FROM "bronze"."Item"
         WHERE "IsDeleted" = false
           AND "IsForSales" = true
           AND "IdNature" IN (1, 2)) AS items_filtered
    """
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", query)
        .options(**JDBC_OPTS)
        .load()
    )


def extract_product_item(spark: SparkSession):
    """Petite table de référence — mise en cache pour le broadcast join."""
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", '"bronze"."ProductItem"')
        .options(**JDBC_OPTS)
        .load()
        .select(
            F.col("Id").alias("ProductItem_Id"),
            F.col("LabelProduct")
        )
        .cache()
    )


def extract_family_mapping(spark: SparkSession):
    """Mapping des Id dupliqués de Family — mise en cache pour le broadcast join."""
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", '"silver"."family_id_mapping"')
        .options(**JDBC_OPTS)
        .load()
        .cache()
    )


def transform(df, df_product, df_family_mapping):
    """
    Ordre des jointures :
      1. ProductItem   → fallback Description, sentinelle -1 si IdProductItem NULL
      2. FamilyMapping → normalisation IdFamily dupliqués
      3. Sentinelle -1 pour IdFamily NULL
      4. Nettoyage Code / Label
    """
    # ── Jointure 1 : ProductItem (broadcast) ──────────────────────────────────
    df = df.join(
        F.broadcast(df_product),
        df["IdProductItem"] == df_product["ProductItem_Id"],
        how="left"
    )
    df = df.withColumn(
        "Description",
        F.coalesce(F.col("Description"), F.col("LabelProduct"))
    ).drop("ProductItem_Id", "LabelProduct")

    # Sentinelle -1 pour IdProductItem NULL
    df = df.withColumn(
        "IdProductItem",
        F.coalesce(F.col("IdProductItem"), F.lit(-1))
    )

    # ── Jointure 2 : Family mapping ───────────────────────────────────────────
    df_family_mapping = df_family_mapping \
        .withColumnRenamed("Id",     "FamilyId_old") \
        .withColumnRenamed("IdKept", "FamilyId_new")

    df = df.join(
        F.broadcast(df_family_mapping),
        df["IdFamily"] == df_family_mapping["FamilyId_old"],
        how="left"
    )
    df = df.withColumn(
        "IdFamily",
        F.coalesce(F.col("FamilyId_new"), F.col("IdFamily"))
    ).drop("FamilyId_old", "FamilyId_new")

    # Sentinelle -1 pour IdFamily NULL
    df = df.withColumn(
        "IdFamily",
        F.coalesce(F.col("IdFamily"), F.lit(-1))
    )

    # ── Nettoyage Code / Label ─────────────────────────────────────────────────
    df = df.withColumn(
        "Code",
        F.when(
            (~F.col("Code").rlike(REGEX) | F.col("Code").isNull()) &
            F.col("Description").rlike(REGEX),
            F.col("Description")
        ).otherwise(F.col("Code"))
    )

    df = df.withColumnRenamed("Description", "Label")

    return df.select(USEFUL_COLS)


def _get_rejected_df(df_clean, res):
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

    elif expectation == "expect_column_values_to_be_between":
        min_val = res["expectation_config"].kwargs.get("min_value")
        max_val = res["expectation_config"].kwargs.get("max_value")
        cond = F.lit(False)
        if min_val is not None:
            cond = cond | (F.col(column) < min_val)
        if max_val is not None:
            cond = cond | (F.col(column) > max_val)
        df_rej = df_clean.filter(cond)
        reason = F.lit(f"{column} invalide — valeur hors bornes [{min_val}, {max_val}]")

    else:
        unexpected_values = res["result"].get("unexpected_list", [])
        if not unexpected_values:
            return None
        df_rej = df_clean.filter(F.col(column).isin(unexpected_values))
        reason = F.lit(f"{column} invalide — {expectation}")

    return df_rej.withColumn("rejection_reason", reason)


def run():
    spark = (
        SparkSession.builder
        .appName("clean_item")
        .config("spark.jars", "/opt/spark/jars/postgresql.jar")
        .config("spark.sql.autoBroadcastJoinThreshold", str(50 * 1024 * 1024))
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("📥 Extraction Bronze...")
    df_raw            = extract(spark)
    df_product        = extract_product_item(spark)
    df_family_mapping = extract_family_mapping(spark)

    # Matérialiser les petites tables en cache avant les joins
    df_product.count()
    df_family_mapping.count()

    print("🔧 Transformation...")
    df_clean = transform(df_raw, df_product, df_family_mapping)

    df_clean.cache()
    n_clean = df_clean.count()
    print(f"   {n_clean} lignes après filtrage")

    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "item_suite", get_item_suite, "item")

    rejected_ids     = set()
    quarantine_table = "quarantine.item_lignes_rejected"

    for res in results["results"]:
        if res["success"]:
            continue
        failed = res["result"].get("unexpected_count", 0)
        if not failed:
            continue
        df_rejected = _get_rejected_df(df_clean, res)
        if df_rejected is None:
            continue
        count = df_rejected.count()
        if count > 0:
            write_silver(df_rejected, quarantine_table)
            print(f"⚠️  {count} lignes rejetées → {quarantine_table}")
            bad_ids = [row["Id"] for row in df_rejected.select("Id").collect()]
            rejected_ids.update(bad_ids)

    if rejected_ids:
        df_silver = df_clean.filter(~F.col("Id").isin(list(rejected_ids)))
        print(f"💾 Écriture Silver ({n_clean - len(rejected_ids)} lignes valides)...")
        write_silver(df_silver, SILVER_TABLE)
    else:
        print(f"💾 Écriture Silver ({n_clean} lignes)...")
        write_silver(df_clean, SILVER_TABLE)

    print("🏁 Pipeline Item terminé avec succès ✅")

    df_clean.unpersist()
    df_product.unpersist()
    df_family_mapping.unpersist()
    spark.stop()


if __name__ == "__main__":
    run()