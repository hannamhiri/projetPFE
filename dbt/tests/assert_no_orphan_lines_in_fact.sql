-- tests/singular/assert_no_orphan_lines_in_fact.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- TEST SINGULIER 4 : Lignes orphelines dans fact_sales
-- Règle : toute ligne de la fact doit avoir un document parent valide dans stg_document.
-- Détecte les cas où une ligne de document existe sans son entête.
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    dl.DocumentLineId,
    dl.DocumentId
FROM {{ ref('stg_document_line') }} dl
LEFT JOIN {{ ref('stg_document') }} d
    ON dl.DocumentId = d.DocumentId
WHERE d.DocumentId IS NULL
