### clean_geographical_area.py ###
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.geographical_area_expectations import get_geographical_area_suite
from utils.quarantine_helper import process_rejections, write_valid_or_all
import psycopg2

SILVER_TABLE = "silver.GeographicalArea"
JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {"user": "warehouse", "password": "warehouse", "driver": "org.postgresql.Driver"}


def extract(spark):
    query = '(SELECT "Id", "Label" FROM "bronze"."GeographicalArea" WHERE "IsDeleted" = false) AS t'
    return spark.read.format("jdbc").option("url", JDBC_URL).option("dbtable", query).options(**JDBC_OPTS).load()

def insert_sentinelles():
    conn = psycopg2.connect(
        host="postgres", port=5432, dbname="warehouse_db",
        user="warehouse", password="warehouse"
    )
    cur = conn.cursor()
    cur.execute("""
       INSERT INTO "silver"."geographicalarea" ("Id", "Label")
        SELECT -1, 'Zone inconnue'
        WHERE NOT EXISTS (
            SELECT 1 FROM "silver"."geographicalarea" WHERE "Id" = -1
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def run():
    spark = SparkSession.builder.appName("clean_geographical_area").config("spark.jars", "/opt/spark/jars/postgresql.jar").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print("📥 Extraction Bronze...")
    df_clean = extract(spark)
    df_clean.cache()
    n_clean = df_clean.count()
    print(f"   {n_clean} lignes")
    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "geographical_area_suite", get_geographical_area_suite, "geographical_area")
    rejected_ids = process_rejections(df_clean, results, "quarantine.geographical_area_lignes_rejected")
    write_valid_or_all(df_clean, rejected_ids, SILVER_TABLE, n_clean)
    df_clean.unpersist()
    insert_sentinelles()
    print("🏁 Pipeline Geographical Area terminé avec succès ✅")
    spark.stop()


if __name__ == "__main__":
    run()
