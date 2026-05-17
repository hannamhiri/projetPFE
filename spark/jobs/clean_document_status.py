### clean_document_status.py ###
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.document_status_expectations import get_document_status_suite
from utils.silver_writer import write_silver
from utils.quarantine_helper import process_rejections, write_valid_or_all

SILVER_TABLE = "silver.DocumentStatus"
JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {"user": "warehouse", "password": "warehouse", "driver": "org.postgresql.Driver"}


def extract(spark):
    query = '(SELECT "Id", "Label" FROM "bronze"."DocumentStatus" WHERE "IsDeleted" = false) AS t'
    return spark.read.format("jdbc").option("url", JDBC_URL).option("dbtable", query).options(**JDBC_OPTS).load()


def run():
    spark = SparkSession.builder.appName("clean_document_status").config("spark.jars", "/opt/spark/jars/postgresql.jar").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print("📥 Extraction Bronze...")
    df_clean = extract(spark)
    df_clean.cache()
    n_clean = df_clean.count()
    print(f"   {n_clean} lignes")
    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "document_status_suite", get_document_status_suite, "document_status")
    rejected_ids = process_rejections(df_clean, results, "quarantine.document_status_lignes_rejected")
    write_valid_or_all(df_clean, rejected_ids, SILVER_TABLE, n_clean)
    df_clean.unpersist()
    print("🏁 Pipeline Document Status terminé avec succès ✅")
    spark.stop()


if __name__ == "__main__":
    run()
