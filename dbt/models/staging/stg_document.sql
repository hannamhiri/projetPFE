SELECT
    Id                  AS DocumentId,
    Code                AS DocumentCode,
    IdDocumentStatus    AS DocumentStatusId,
    DocumentTypeCode,
    IdTiers             AS ClientId,
    DocumentDate,
    IsForPos
FROM {{ source('silver', 'document') }}