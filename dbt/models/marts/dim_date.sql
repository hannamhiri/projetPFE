
-- Dimension Date générée depuis les dates distinctes de stg_document
-- Surrogate Key = YYYYMMDD (entier naturel, pratique pour les cubes OLAP)


SELECT
    toInt32(toYYYYMMDD(DocumentDate))               AS DateSK,      -- SK = YYYYMMDD (ex: 20240315)
    DocumentDate                                    AS DateBK,
    toDayOfMonth(DocumentDate)                      AS Day,
    toMonth(DocumentDate)                           AS Month,
    CASE toMonth(DocumentDate)
        WHEN 1  THEN 'Janvier'   WHEN 2  THEN 'Février'
        WHEN 3  THEN 'Mars'      WHEN 4  THEN 'Avril'
        WHEN 5  THEN 'Mai'       WHEN 6  THEN 'Juin'
        WHEN 7  THEN 'Juillet'   WHEN 8  THEN 'Août'
        WHEN 9  THEN 'Septembre' WHEN 10 THEN 'Octobre'
        WHEN 11 THEN 'Novembre'  WHEN 12 THEN 'Décembre'
    END                                             AS MonthName,
    toQuarter(DocumentDate)                         AS Quarter,
    toYear(DocumentDate)                            AS Year,
    CASE toDayOfWeek(DocumentDate)  -- 1=Lundi ... 7=Dimanche (ISO)
        WHEN 1 THEN 'Lundi'      WHEN 2 THEN 'Mardi'
        WHEN 3 THEN 'Mercredi'   WHEN 4 THEN 'Jeudi'
        WHEN 5 THEN 'Vendredi'   WHEN 6 THEN 'Samedi'
        WHEN 7 THEN 'Dimanche'
    END                                             AS DayName
FROM (
    SELECT DISTINCT DocumentDate
    FROM {{ ref('stg_document') }}
    WHERE DocumentDate IS NOT NULL
)
