def write_silver(df, table: str):
    """
    Écrit un DataFrame PySpark dans le schéma silver de PostgreSQL.
    table : ex. "silver.item"
    """
    (
        df.write
        .format("jdbc")
        .option("url", "jdbc:postgresql://postgres:5432/warehouse_db")
        .option("dbtable", table)
        .option("user", "warehouse")
        .option("password", "warehouse")
        .option("driver", "org.postgresql.Driver")
        .mode("overwrite")
        .save()
    )
    print(f" Écriture terminée → {table}")