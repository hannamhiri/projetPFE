cube(`DimClient`, {
  sql_table: `gold.dim_client`,

  measures: {
    clientCount: {
        type: `count`,
        title: `Nb Clients`
    }
  },

  dimensions: {
    clientSK: {
      sql: `ClientSK`,
      type: `number`,
      primaryKey: true,
    },
    clientBK: {
      sql: `ClientBK`,
      type: `number`,
      title: `ID Client`,
    },
    clientCode: {
      sql: `ClientCode`,
      type: `string`,
      title: `Code Client`,
    },
    clientName: {
      sql: `ClientName`,
      type: `string`,
      title: `Nom Client`,
    },
    isActive: {
      sql: `IsActive`,
      type: `number`,
      title: `Actif`,
    },
    isBTOB: {
      sql: `IsBTOB`,
      type: `number`,
      title: `B2B`,
    },
    
  },

  refreshKey: {
    every: `24 hours`,
  },
});