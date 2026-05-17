SELECT
    Id      AS DocumentStatusId,
    Label    AS DocumentStatusLabel
FROM {{ source('silver', 'documentstatus') }}