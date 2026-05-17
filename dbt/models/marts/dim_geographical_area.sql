-- Reliée directement à fact_sales (via lookup sur ClientId → IdGeographicalArea)
-- Surrogate Key générée depuis GeographicalAreaId (BK source)

SELECT
    ROW_NUMBER() OVER (ORDER BY GeographicalAreaId)  AS GeographicalAreaSK,
    GeographicalAreaId                                              AS GeographicalAreaBK,
    GeographicalAreaLabel
FROM {{ ref('stg_geographical_area') }}
