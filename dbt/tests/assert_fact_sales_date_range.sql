-- tests/singular/assert_fact_sales_date_range.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- TEST SINGULIER 3 : Dates de vente dans une plage raisonnable
-- Règle : aucune vente ne doit avoir une date antérieure à 2000
--         ni supérieure à la date du jour (pas de données futures).
-- Adapté pour ClickHouse.
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    fs.DateSK,
    dd.DateBK
FROM {{ ref('fact_sales') }} fs
INNER JOIN {{ ref('dim_date') }} dd ON fs.DateSK = dd.DateSK
WHERE dd.DateBK < toDate('2000-01-01')
   OR dd.DateBK > today()
