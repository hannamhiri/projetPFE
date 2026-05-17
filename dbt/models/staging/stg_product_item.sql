SELECT
    Id              AS ProductItemId,
    LabelProduct    AS ProductLabel
FROM {{ source('silver', 'productitem') }}