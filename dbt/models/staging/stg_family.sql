SELECT
    Id      AS FamilyId,
    Code    AS FamilyCode,
    Label   AS FamilyLabel
FROM {{ source('silver', 'family') }}