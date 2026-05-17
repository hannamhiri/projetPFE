
SELECT
    ROW_NUMBER() OVER (ORDER BY WarehouseId)     AS WarehouseSK,
    WarehouseId                                                 AS WarehouseBK,
    WarehouseCode,
    WarehouseName
FROM {{ ref('stg_warehouse') }}
