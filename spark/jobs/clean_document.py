from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.document_expectations import get_document_suite
from utils.silver_writer import write_silver

SILVER_TABLE = "silver.Document"
USEFUL_COLS  = ["Id", "Code", "IdDocumentStatus", "DocumentTypeCode",
                "IdTiers", "DocumentDate", "DocumentHTPrice", "IsForPos"]

JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {
    "user": "warehouse",
    "password": "warehouse",
    "driver": "org.postgresql.Driver"
}


def extract(spark: SparkSession):
    """
    Optimisation : pushdown SQL — filtre IsDeleted et DocumentTypeCode côté PostgreSQL,
    et ne transfère que les colonnes utiles + CreationDate (nécessaire pour correction date).
    """
    query = """
        (SELECT "Id", "Code", "IdDocumentStatus", "DocumentTypeCode",
                "IdTiers", "DocumentDate", "DocumentHTPrice", "IsForPos", "CreationDate"
         FROM "bronze"."Document"
         WHERE "IsDeleted" = false
           AND "DocumentTypeCode" LIKE '%SA%') AS doc_filtered
    """
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", query)
        .options(**JDBC_OPTS)
        .load()
    )


def transform(df):
    # Toutes les transformations regroupées en une seule passe withColumns
    df = df.withColumns({
        "IsForPos":       F.col("IsForPos").cast("int"),
        "DocumentDate":   F.col("DocumentDate").cast("date"),
        "DocumentHTPrice": F.round(F.col("DocumentHTPrice").cast("double"), 4),
    })

    # Correction dates aberrantes
    df = df.withColumn(
        "DocumentDate",
        F.when(
            (F.year(F.col("DocumentDate")) == 1970) |
            (F.col("DocumentDate") > F.current_date()),
            F.to_date(F.col("CreationDate"))
        ).otherwise(F.col("DocumentDate"))
    )

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
        .appName("clean_document")
        .config("spark.jars", "/opt/spark/jars/postgresql.jar")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("📥 Extraction Bronze (avec pushdown SQL)...")
    df_raw = extract(spark)

    print("🔧 Transformation...")
    df_clean = transform(df_raw)

    # CACHE : évite de recalculer df_clean à chaque action GX + écriture
    df_clean.cache()
    n_clean = df_clean.count()
    print(f"   {n_clean} lignes après filtrage")

    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "document_suite", get_document_suite, "document")

    rejected_ids     = set()
    quarantine_table = "quarantine.document_lignes_rejected"

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
        df_valid = df_clean.filter(~F.col("Id").isin(list(rejected_ids)))
        print(f"💾 Écriture Silver ({n_clean - len(rejected_ids)} lignes valides)...")
        write_silver(df_valid, SILVER_TABLE)
    else:
        print(f"💾 Écriture Silver ({n_clean} lignes)...")
        write_silver(df_clean, SILVER_TABLE)

    df_clean.unpersist()
    print("🏁 Pipeline Document terminé avec succès ✅")
    spark.stop()


if __name__ == "__main__":
    run()
