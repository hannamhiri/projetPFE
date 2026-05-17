SELECT
    row_number() OVER (ORDER BY DocumentStatusId)   AS DocumentStatusSK,
    DocumentStatusId                                                AS DocumentStatusBK,
    DocumentStatusLabel
FROM {{ ref('stg_document_status') }}
