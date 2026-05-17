SELECT
    Id                      AS DocumentLineId,
    IdDocument              AS DocumentId,
    IdItem                  AS ItemId,
    MovementQty             AS Quantity,
    HtTotalLine             AS LinePrice,
    CostPrice,
    DiscountPercentage,
    IdWarehouse             AS WarehouseId
FROM {{ source('silver', 'documentline') }}