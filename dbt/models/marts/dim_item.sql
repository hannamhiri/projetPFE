-- Dimension Article enrichie avec ProductItem (Brand) et Family
-- Surrogate Key (SK) générée via dbt_utils.generate_surrogate_key

SELECT
    ROW_NUMBER() OVER (ORDER BY ItemId)      AS ItemSK,
    ItemId                                                  AS ItemBK,
    ItemCode,
    ItemLabel,
    p.ProductLabel                                         AS Brand,
   
    f.FamilyLabel                                           AS Family
FROM {{ ref('stg_item') }} i
LEFT JOIN {{ ref('stg_product_item') }} p
    ON i.ProductItemId = p.ProductItemId
LEFT JOIN {{ ref('stg_family') }} f
    ON i.FamilyId = f.FamilyId
