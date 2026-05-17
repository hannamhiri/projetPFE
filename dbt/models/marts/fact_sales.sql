-- models/marts/fact_sales.sql
-- Table de Faits : Ventes
-- Granularité : 1 ligne par ligne de document (DocumentLineId)
--
-- Corrections :
--   1. CostPrice → CostPrice * Quantity (coût total ligne, pas unitaire)
--   2. LEFT JOIN sur les dimensions pouvant avoir des sentinelles -1
--      (warehouse, geographical_area, client)
{{ config(
    order_by='(DateSK, GeographicalAreaSK, ClientSK, ItemSK)',
    settings={'allow_nullable_key': 1},
) }}

SELECT
    -- ── Surrogate Keys (FK vers dimensions) ──────────────────────────────────
    dc.ClientSK                AS ClientSK,
    di.ItemSK                  AS ItemSK,
    ddt.DocumentTypeSK         AS DocumentTypeSK,
    dds.DocumentStatusSK       AS DocumentStatusSK,
    dga.GeographicalAreaSK     AS GeographicalAreaSK,
    dd.DateSK                  AS DateSK,
    dw.WarehouseSK             AS WarehouseSK,

    -- ── Attributs dégénérés ──────────────────────────────────────────────────
    d.DocumentCode             AS DocumentCode,
    d.IsForPos                 AS IsForPos,

    -- ── Mesures ──────────────────────────────────────────────────────────────
    dl.Quantity                                                    AS Quantity,
    dl.LinePrice                                                   AS LinePrice,
    -- CostPrice total de la ligne (unitaire × quantité)
    -- NULL si CostPrice non renseigné (pas de coalesce → marge partielle visible)
    dl.CostPrice * dl.Quantity                                     AS CostPrice,
    ROUND(dl.LinePrice * dl.DiscountPercentage / 100.0, 4)        AS DiscountAmount,
    dl.DiscountPercentage                                          AS DiscountPercentage

FROM {{ ref('stg_document_line') }} dl

INNER JOIN {{ ref('stg_document') }} d
    ON dl.DocumentId = d.DocumentId

-- ── Dimensions obligatoires (pas de sentinelle -1 possible) ──────────────────
INNER JOIN {{ ref('dim_client') }} dc
    ON d.ClientId = dc.ClientBK

INNER JOIN {{ ref('dim_item') }} di
    ON dl.ItemId = di.ItemBK

INNER JOIN {{ ref('dim_document_type') }} ddt
    ON d.DocumentTypeCode = ddt.DocumentTypeBK

INNER JOIN {{ ref('dim_document_status') }} dds
    ON d.DocumentStatusId = dds.DocumentStatusBK

INNER JOIN {{ ref('dim_date') }} dd
    ON toInt32(toYYYYMMDD(d.DocumentDate)) = dd.DateSK

-- ── Dimensions avec sentinelle -1 possible → LEFT JOIN ───────────────────────
-- IdWarehouse peut valoir -1 (122297 lignes sans entrepôt)
LEFT JOIN {{ ref('dim_warehouse') }} dw
    ON dl.WarehouseId = dw.WarehouseBK

-- GeographicalAreaId peut valoir -1 (clients sans zone)
LEFT JOIN {{ ref('stg_client') }} c
    ON d.ClientId = c.ClientId
LEFT JOIN {{ ref('dim_geographical_area') }} dga
    ON c.GeographicalAreaId = dga.GeographicalAreaBK