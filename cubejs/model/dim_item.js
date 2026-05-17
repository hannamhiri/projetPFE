cube(`DimItem`, {
  sql_table: `gold.dim_item`,

  measures: {
    itemCount: {
      type: `count`,
      title: `Nb Articles`,
    },
    nbFamilles: {
    sql: `Family`,
    type: `countDistinct`,
    title: `Nb Familles`
  },

    nbBrands: {
    sql: `Brand`,
    type: `countDistinct`,
    title: `Nb Marques`
  },
  },

  dimensions: {
    itemSK: {
      sql: `ItemSK`,
      type: `number`,
      primaryKey: true,
    },
    itemBK: {
      sql: `ItemBK`,
      type: `number`,
      title: `ID Article`,
    },
    itemCode: {
      sql: `ItemCode`,
      type: `string`,
      title: `Code Article`,
    },
    itemLabel: {
      sql: `ItemLabel`,
      type: `string`,
      title: `Libellé Article`,
    },
    brand: {
      sql: `Brand`,
      type: `string`,
      title: `Marque`,
    },
    family: {
      sql: `Family`,
      type: `string`,
      title: `Famille`,
    },
  
  },

  refreshKey: {
    every: `24 hours`,
  },
});