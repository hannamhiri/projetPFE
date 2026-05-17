SELECT
    row_number() OVER (ORDER BY ClientId)    AS ClientSK,
    ClientId                                 AS ClientBK,
    ClientCode,
    ClientName,
    IsActive,
    IsBTOB
FROM {{ ref('stg_client') }}
