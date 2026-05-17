SELECT
    Id              AS ItemId,
    Code            AS ItemCode,
    Label           AS ItemLabel,
    IdProductItem   AS ProductItemId,
    IdFamily        AS FamilyId
FROM {{ source('silver', 'item') }}