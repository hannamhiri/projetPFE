from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.document_type_expectations import get_document_type_suite
from utils.silver_writer import write_silver
from utils.quarantine_helper import process_rejections, write_valid_or_all

SILVER_TABLE = "silver.DocumentType"
JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {"user": "warehouse", "password": "warehouse", "driver": "org.postgresql.Driver"}


def extract(spark):
    query = """
        (SELECT "Code", "Label"
         FROM "bronze"."DocumentType"
         WHERE "IsDeleted" = false
           AND "Code" LIKE '%SA%') AS t
    """
    return spark.read.format("jdbc").option("url", JDBC_URL).option("dbtable", query).options(**JDBC_OPTS).load()


def run():
    spark = SparkSession.builder.appName("clean_document_type").config("spark.jars", "/opt/spark/jars/postgresql.jar").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print("📥 Extraction Bronze...")
    df_clean = extract(spark)
    df_clean.cache()
    n_clean = df_clean.count()
    print(f"   {n_clean} lignes")
    print("🔍 Validation GX...")
    results = run_ge_validation(df_clean, "document_type_suite", get_document_type_suite, "document_type")
    # DocumentType utilise Code comme PK
    rejected_codes = process_rejections(df_clean, results, "quarantine.document_type_lignes_rejected", pk_col="Code")
    write_valid_or_all(df_clean, rejected_codes, SILVER_TABLE, n_clean, pk_col="Code")
    df_clean.unpersist()
    print("🏁 Pipeline Document Type terminé avec succès ✅")
    spark.stop()


if __name__ == "__main__":
    run()
