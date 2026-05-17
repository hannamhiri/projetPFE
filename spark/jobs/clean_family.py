from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.family_expectations import get_family_suite
from utils.silver_writer import write_silver
from utils.quarantine_helper import process_rejections, write_valid_or_all
import psycopg2

SILVER_TABLE = "silver.Family"
JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {"user": "warehouse", "password": "warehouse", "driver": "org.postgresql.Driver"}


def extract(spark):
    query = """
        (SELECT "Id", "Code", "Label"
         FROM "bronze"."Family"
         WHERE "IsDeleted" = false) AS t
    """
    return spark.read.format("jdbc").option("url", JDBC_URL).option("dbtable", query).options(**JDBC_OPTS).load()


def transform(df):
    window = Window.partitionBy("Code").orderBy("Id")
    df = df.withColumn("rn", F.row_number().over(window))

    # Mapping : doublons seulement (Id != IdKept)
    df_mapping = (
        df.alias("all")
        .join(
            df.filter(F.col("rn") == 1)
              .select(F.col("Code").alias("Code_ref"), F.col("Id").alias("IdKept")),
            F.col("Code") == F.col("Code_ref"),
            how="left"
        )
        .select("Id", "IdKept")
        .filter(F.col("Id") != F.col("IdKept"))
    )

    df_clean = df.filter(F.col("rn") == 1).drop("rn")
    return df_clean, df_mapping

def insert_sentinelles():
    conn = psycopg2.connect(
        host="postgres", port=5432, dbname="warehouse_db",
        user="warehouse", password="warehouse"
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO "silver"."family" ("Id", "Code", "Label")
        SELECT -1, 'UNKNOWN', 'Famille inconnue'
        WHERE NOT EXISTS (
            SELECT 1 FROM "silver"."family" WHERE "Id" = -1
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def run():
    spark = (
        SparkSession.builder
        .appName("clean_family")
        .config("spark.jars", "/opt/spark/jars/postgresql.jar")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("📥 Extraction Bronze...")
    df_raw = extract(spark)

    print("🔧 Transformation...")
    df_clean, df_mapping = transform(df_raw)

    # Mettre en cache df_clean ET df_mapping (les deux sont réutilisés)
    df_clean.cache()
    df_mapping.cache()

    n_clean   = df_clean.count()
    n_mapping = df_mapping.count()
    print(f"   {n_clean} lignes après déduplication, {n_mapping} mappings")

    write_silver(df_mapping, "silver.family_id_mapping")
    print(f"   Mappings sauvegardés → silver.family_id_mapping")

    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "Family_suite", get_family_suite, "Family")

    # Log détaillé des règles échouées (conservé depuis l'original)
    for res in results["results"]:
        if res["success"]:
            continue
        exp    = res["expectation_config"].type
        col    = res["expectation_config"].kwargs.get("column", "N/A")
        total  = res["result"].get("element_count", 0)
        failed = res["result"].get("unexpected_count", 0)
        if failed:
            pct = (failed / total) * 100 if total > 0 else 0
            print(f"{'─'*50}\nRègle: {exp} | Colonne: {col} | {failed}/{total} ({pct:.4f}%)")

    rejected_ids = process_rejections(df_clean, results, "quarantine.family_lignes_rejected")
    write_valid_or_all(df_clean, rejected_ids, SILVER_TABLE, n_clean)

    df_clean.unpersist()
    df_mapping.unpersist()
    insert_sentinelles()
    print("🏁 Pipeline Family terminé avec succès ✅")
    spark.stop()


if __name__ == "__main__":
    run()
