cube(`DimDate`, {
  sql_table: `gold.dim_date`,

  dimensions: {
    dateSK: {
      sql: `DateSK`,
      type: `number`,
      primaryKey: true,
    },
    dateComplete: {
      sql: `DateBK`,
      type: `time`,
      title: `Date`,
    },
    day: {
      sql: `Day`,
      type: `number`,
      title: `Jour`,
    },
    month: {
      sql: `Month`,
      type: `number`,
      title: `Mois (numéro)`,
    },
    monthName: {
      sql: `MonthName`,
      type: `string`,
      title: `Mois`,
    },
    quarter: {
      sql: `Quarter`,
      type: `number`,
      title: `Trimestre`,
    },
    year: {
      sql: `Year`,
      type: `number`,
      title: `Année`,
    },
    dayName: {
      sql: `DayName`,
      type: `string`,
      title: `Jour de la semaine`,
    },
   
  },

  refreshKey: {
    every: `3650 days`,
  },
});