SELECT
    ROW_NUMBER() OVER (ORDER BY DocumentTypeCode)   AS DocumentTypeSK,
    DocumentTypeCode                                                AS DocumentTypeBK,
    DocumentTypeLabel                                               AS DocumentTypeLabel
FROM {{ ref('stg_document_type') }}
