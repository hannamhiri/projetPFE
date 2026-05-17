SELECT
    Code    AS DocumentTypeCode,
    Label   AS DocumentTypeLabel
FROM {{ source('silver', 'documenttype') }}