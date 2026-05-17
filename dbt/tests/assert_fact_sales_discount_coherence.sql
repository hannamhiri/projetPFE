-- tests/singular/assert_fact_sales_discount_coherence.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- TEST SINGULIER 2 : Cohérence entre DiscountAmount et DiscountPercentage
-- Règle : si DiscountPercentage = 0 alors DiscountAmount doit être 0 (ou null).
-- Détecte les incohérences de calcul de remise.
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    LinePrice,
    DiscountPercentage,
    DiscountAmount
FROM {{ ref('fact_sales') }}
WHERE (DiscountPercentage = 0 OR DiscountPercentage IS NULL)
  AND DiscountAmount > 0
