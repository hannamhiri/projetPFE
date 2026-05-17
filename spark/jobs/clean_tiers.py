from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.tiers_expectations import get_tiers_suite
from utils.silver_writer import write_silver
from utils.quarantine_helper import process_rejections, write_valid_or_all

SILVER_TABLE = "silver.Client"
USEFUL_COLS  = ["Id", "Code", "Name", "IdGeographicalArea", "IsBTOB", "IsActive", "Adress"]

JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {
    "user": "warehouse",
    "password": "warehouse",
    "driver": "org.postgresql.Driver"
}


def extract(spark: SparkSession):
    """Pushdown SQL : filtre IsDeleted et IdTypeTiers côté PostgreSQL."""
    query = """
        (SELECT "Id", "CodeTiers", "Name", "IdGeographicalArea",
                "IsBTOB", "IsActive", "Adress"
         FROM "bronze"."Tiers"
         WHERE "IsDeleted" = false
           AND "IdTypeTiers" = 1) AS tiers_filtered
    """
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", query)
        .options(**JDBC_OPTS)
        .load()
    )


def transform(df):
    df = df.withColumns({
        "IsBTOB":   F.col("IsBTOB").cast("int"),
        "IsActive": F.col("IsActive").cast("int"),
        # Règles métier IdGeographicalArea en une seule chaîne when/otherwise
        "IdGeographicalArea": F.when(F.col("Name") == "PASSAGER", F.lit(7))
                                .when(F.col("Adress") == "RTE MAHDIA KM1 EL BOUSTEN", F.lit(3))
                                .when(F.col("IdGeographicalArea").isNull(), F.lit(-1))   # ← sentinelle
                                .otherwise(F.col("IdGeographicalArea")),
                                })
    return df.withColumnRenamed("CodeTiers", "Code").select(USEFUL_COLS)


def run():
    spark = (
        SparkSession.builder
        .appName("clean_tiers")
        .config("spark.jars", "/opt/spark/jars/postgresql.jar")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("📥 Extraction Bronze (avec pushdown SQL)...")
    df_raw   = extract(spark)

    print("🔧 Transformation...")
    df_clean = transform(df_raw)
    df_clean.cache()
    n_clean  = df_clean.count()
    print(f"   {n_clean} lignes après filtrage")

    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "tiers_suite", get_tiers_suite, "tiers")

    quarantine_table = "quarantine.tiers_lignes_rejected"
    rejected_ids = process_rejections(df_clean, results, quarantine_table)
    write_valid_or_all(df_clean, rejected_ids, SILVER_TABLE, n_clean)

    df_clean.unpersist()
    print("🏁 Pipeline Tiers terminé avec succès ✅")
    spark.stop()


if __name__ == "__main__":
    run()