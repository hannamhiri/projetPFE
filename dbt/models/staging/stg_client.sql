SELECT
    Id                  AS ClientId,
    Code           AS ClientCode,
    Name                AS ClientName,
    IdGeographicalArea AS GeographicalAreaId,
    IsBTOB,
    IsActive
FROM {{ source('silver', 'client') }}