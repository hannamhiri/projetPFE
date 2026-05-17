-- tests/singular/assert_fact_sales_no_negative_priceTT.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- TEST SINGULIER 1 : PriceHT cohérent avec Quantity
-- Règle métier : une ligne de vente (Quantity > 0) ne peut pas avoir un PriceHT négatif.
-- Les retours (Quantity < 0) peuvent avoir un PriceHT négatif — c'est normal.
-- Retourne les lignes en anomalie (le test échoue si le résultat n'est pas vide).
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    DocumentCode,
    Quantity,
    LinePrice
FROM {{ ref('fact_sales') }}
WHERE Quantity > 0
  AND LinePrice < 0
