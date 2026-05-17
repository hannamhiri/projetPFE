from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from utils.ge_runner import run_ge_validation
from expectations.document_line_expectations import get_document_line_suite
from utils.silver_writer import write_silver

BRONZE_TABLE = '"bronze"."DocumentLine"'
SILVER_TABLE = "silver.DocumentLine"
USEFUL_COLS  = [
    "Id", "IdDocument", "IdItem", "IdWarehouse",
    "MovementQty", "DiscountPercentage", "HtTotalLine", "CostPrice",
    "IdDocumentLineStatus", "IdDocumentLineAssociated",
]

JDBC_URL  = "jdbc:postgresql://postgres:5432/warehouse_db"
JDBC_OPTS = {
    "user": "warehouse",
    "password": "warehouse",
    "driver": "org.postgresql.Driver"
}

BROADCAST_THRESHOLD = 50 * 1024 * 1024   # 50 MB


def extract(spark: SparkSession):
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", BRONZE_TABLE)
        .options(**JDBC_OPTS)
        .option("partitionColumn", "IdDocument")
        .option("lowerBound", "1")
        .option("upperBound", "9999999")
        .option("numPartitions", "8")
        .load()
    )


def extract_document_types(spark: SparkSession):
    """
    Récupère DocumentTypeCode + IsRestaurn par document.
    IsRestaurn est nécessaire pour la règle 2a (IA-SA restaurant → négatif).
    """
    query = """
        (SELECT "Id"               AS "DocId",
                "DocumentTypeCode",
                "IsRestaurn"
         FROM   "bronze"."Document"
         WHERE  "IsDeleted" = false
           AND  "DocumentTypeCode" IN ('I-SA', 'A-SA', 'IA-SA', 'D-SA')) AS doc_types
    """
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", query)
        .options(**JDBC_OPTS)
        .load()
        .cache()
    )


def extract_associated_line_types(spark: SparkSession):
    """
    Pour chaque ligne ayant une ligne associée, récupère le DocumentTypeCode
    de cette ligne associée (nécessaire pour la règle 2b : IA-SA lié à un A-SA).

    Jointure : DocumentLine.IdDocumentLineAssociated → DocumentLine2.Id → Document.DocumentTypeCode
    Retourne : LineId (Id de la ligne principale) + AssocType (type de la ligne associée)
    """
    query = """
        (SELECT dl."Id"               AS "LineId",
                d."DocumentTypeCode"  AS "AssocType"
         FROM   "bronze"."DocumentLine" dl
         JOIN   "bronze"."DocumentLine" dl2
                ON  dl."IdDocumentLineAssociated" = dl2."Id"
                AND dl2."IsDeleted" = false
         JOIN   "bronze"."Document" d
                ON  dl2."IdDocument" = d."Id"
                AND d."IsDeleted" = false
         WHERE  dl."IsDeleted" = false
           AND  dl."IdDocumentLineAssociated" IS NOT NULL) AS assoc_types
    """
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", query)
        .options(**JDBC_OPTS)
        .load()
        .cache()
    )


def transform(df, df_doc_types, df_assoc_types):
    # ── 0. Filtre de base ─────────────────────────────────────────────────────
    df = df.filter(F.col("IsDeleted") == False)

    # ── 1. Jointure DocumentTypeCode + IsRestaurn (broadcast) ─────────────────
    df = df.join(
        F.broadcast(df_doc_types),
        df["IdDocument"] == df_doc_types["DocId"],
        how="left"
    ).drop("DocId")

    # ── 2. Jointure IdDocumentLineAssociatedType (broadcast) ──────────────────
    df = df.join(
        F.broadcast(
            df_assoc_types.withColumnRenamed("AssocType", "IdDocumentLineAssociatedType")
        ),
        df["Id"] == df_assoc_types["LineId"],
        how="left"
    ).drop("LineId")

    # ── 3. Coalesce nulls avant calcul de signe ───────────────────────────────
    df = df.withColumns({
        "HtTotalLine":        F.coalesce(F.col("HtTotalLine").cast("double"),        F.lit(0.0)),
        "DiscountPercentage": F.coalesce(F.col("DiscountPercentage").cast("double"), F.lit(0.0)),
        "MovementQty":        F.coalesce(F.col("MovementQty").cast("double"),        F.lit(0.0)),
        "CostPrice":          F.coalesce(F.col("CostPrice").cast("double"),          F.lit(0.0)),
    })
    # Sentinelle -1 pour IdWarehouse NULL
    df = df.withColumn(
            "IdWarehouse",
            F.coalesce(F.col("IdWarehouse"), F.lit(-1))
        )

    # ── Condition partagée pour les règles 2a et 2b ───────────────────────────
    cond_2a = (F.col("DocumentTypeCode") == "IA-SA") & (F.col("IsRestaurn") == 1)
    cond_2b = (
        (F.col("DocumentTypeCode") == "IA-SA") &
        F.col("IdDocumentLineAssociated").isNotNull() &
        (F.col("IdDocumentLineAssociatedType") == "A-SA")
    )

    # ── 4. Gestion du signe HtTotalLine ──────────────────────────────────────
    #   Règle 1  : A-SA               → toujours négatif
    #   Règle 2a : IA-SA + restaurant → négatif
    #   Règle 2b : IA-SA + assoc A-SA → négatif
    #   Règle 3/4: I-SA, D-SA         → positif (inchangé)
    df = df.withColumn(
        "HtTotalLine",
        F.when(F.col("DocumentTypeCode") == "A-SA", -F.col("HtTotalLine"))
         .when(cond_2a, -F.col("HtTotalLine"))
         .when(cond_2b, -F.col("HtTotalLine"))
         .otherwise(F.col("HtTotalLine"))
    )

    # ── 5. Gestion du signe MovementQty (même logique) ────────────────────────
    df = df.withColumn(
        "MovementQty",
        F.when(F.col("DocumentTypeCode") == "A-SA", -F.col("MovementQty"))
         .when(cond_2a, -F.col("MovementQty"))
         .when(cond_2b, -F.col("MovementQty"))
         .otherwise(F.col("MovementQty"))
    )

    # ── 6. Gestion du signe CostPrice (suit la même logique) ─────────────────
    df = df.withColumn(
        "CostPrice",
        F.when(F.col("DocumentTypeCode") == "A-SA", -F.col("CostPrice"))
         .when(cond_2a, -F.col("CostPrice"))
         .when(cond_2b, -F.col("CostPrice"))
         .otherwise(F.col("CostPrice"))
    )

    # ── 7. Arrondi final ──────────────────────────────────────────────────────
    df = df.withColumns({
        "HtTotalLine":        F.round(F.col("HtTotalLine"),        4),
        "CostPrice":          F.round(F.col("CostPrice"),          4),
        "DiscountPercentage": F.round(F.col("DiscountPercentage"), 4),
        "MovementQty":        F.col("MovementQty").cast("int"),
    })

    # ── 8. Normalisation IdDocumentLineAssociated (sentinelles pour les NULL) ─
    #   -1 : Facture (I-SA)       sans BL lié
    #   -2 : Avoir (A-SA)         sans facture liée
    #   -3 : Avoir facture (IA-SA) sans avoir lié
    df = df.withColumn(
        "IdDocumentLineAssociated",
        F.when(
            (F.col("DocumentTypeCode") == "I-SA") &
            F.col("IdDocumentLineAssociated").isNull(), F.lit(-1)
        ).when(
            (F.col("DocumentTypeCode") == "A-SA") &
            F.col("IdDocumentLineAssociated").isNull(), F.lit(-2)
        ).when(
            (F.col("DocumentTypeCode") == "IA-SA") &
            F.col("IdDocumentLineAssociated").isNull(), F.lit(-3)
        ).otherwise(F.col("IdDocumentLineAssociated"))
    )

    # ── 9. Nettoyage colonnes temporaires ─────────────────────────────────────
    df = df.drop("DocumentTypeCode", "IsRestaurn", "IdDocumentLineAssociatedType")

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
        .appName("clean_document_line")
        .config("spark.jars", "/opt/spark/jars/postgresql.jar")
        .config("spark.driver.memory", "4g")
        .config("spark.executor.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.autoBroadcastJoinThreshold", str(BROADCAST_THRESHOLD))
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    quarantine_table = "quarantine.document_line_lignes_rejected"

    try:
        # ── Extraction ────────────────────────────────────────────────────────
        print("📥 Extraction Bronze...")
        df_raw         = extract(spark)
        df_doc_types   = extract_document_types(spark)
        df_assoc_types = extract_associated_line_types(spark)

        # Matérialiser les petites tables avant les broadcast joins
        df_doc_types.count()
        df_assoc_types.count()

        # ── Transformation ────────────────────────────────────────────────────
        print("🔧 Transformation...")
        df_clean = transform(df_raw, df_doc_types, df_assoc_types)

        df_clean.cache()
        n_clean = df_clean.count()
        print(f"   {n_clean} lignes après filtrage")

        # ── Validation GX ─────────────────────────────────────────────────────
        print("🔍 Validation GX...")
        results = run_ge_validation(df_clean, "document_line_suite", get_document_line_suite, "document_line")

        rejected_ids = set()

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

        # ── Écriture Silver ───────────────────────────────────────────────────
        if rejected_ids:
            df_valid = df_clean.filter(~F.col("Id").isin(list(rejected_ids)))
            print(f"💾 Écriture Silver ({n_clean - len(rejected_ids)} lignes valides)...")
            write_silver(df_valid, SILVER_TABLE)
        else:
            print(f"💾 Écriture Silver ({n_clean} lignes)...")
            write_silver(df_clean, SILVER_TABLE)

        print("🏁 Pipeline Document Line terminé avec succès ✅")

    except Exception as e:
        print(f"❌ ERREUR pipeline : {e}")
        print("⚠️  Tentative d'écriture en quarantine...")
        try:
            if "df_clean" in locals():
                write_silver(df_clean, quarantine_table)
                print(f"✅ Données écrites en quarantine → {quarantine_table}")
            elif "df_raw" in locals():
                write_silver(df_raw, quarantine_table)
                print(f"✅ Données brutes écrites en quarantine → {quarantine_table}")
            else:
                print("❌ Aucune donnée disponible pour la quarantine")
        except Exception as qe:
            print(f"❌ Erreur écriture quarantine : {qe}")
        raise

    finally:
        if "df_clean" in locals():
            df_clean.unpersist()
        if "df_doc_types" in locals():
            df_doc_types.unpersist()
        if "df_assoc_types" in locals():
            df_assoc_types.unpersist()
        spark.stop()


if __name__ == "__main__":
    run()