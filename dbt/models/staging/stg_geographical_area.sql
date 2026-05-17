SELECT
    Id      AS GeographicalAreaId,
    Label   AS GeographicalAreaLabel
FROM {{ source('silver', 'geographicalarea') }}