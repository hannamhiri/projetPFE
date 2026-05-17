SELECT
    Id as WarehouseId,
    WarehouseCode,
    WarehouseName 
FROM {{ source('silver', 'warehouse') }}