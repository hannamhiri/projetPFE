// ── DimDocumentStatus ────────────────────────────────────────

cube(`DimDocumentStatus`, {
  sql_table: `gold.dim_document_status`,

  measures: {
    documentStatusCount: { type: `count`,
       title: `Nb Statut Document`
     },
  },

  dimensions: {
    documentStatusSK: {
      sql: `DocumentStatusSK`,
      type: `number`,
      primaryKey: true,
    },
    documentStatusBK: {
      sql: `DocumentStatusBK`,
      type: `number`,
      title: `ID Statut`,
    },
    documentStatusLabel: {
      sql: `DocumentStatusLabel`,
      type: `string`,
      title: `Statut Document`,
    },
    
  },

  refreshKey: {
    every: `24 hours`,
  },
});


// ── DimDocumentType ──────────────────────────────────────────

cube(`DimDocumentType`, {
  sql_table: `gold.dim_document_type`,

  measures: {
    DocumentTypeCount: { 
       type: `count`,
       title: `Nb Type Document`
     },
  },

  dimensions: {
    documentTypeSK: {
      sql: `DocumentTypeSK`,
      type: `number`,
      primaryKey: true,
    },
    documentTypeBK: {
      sql: `DocumentTypeBK`,
      type: `string`,
      title: `Code Type`,
    },
    documentTypeLabel: {
      sql: `DocumentTypeLabel`,
      type: `string`,
      title: `Type Document`,
    },
   
   
  },

  refreshKey: {
    every: `24 hours`,
  },
});


// ── DimGeographicalArea ──────────────────────────────────────

cube(`DimGeographicalArea`, {
  sql_table: `gold.dim_geographical_area`,

  measures: {
    geographicalAreaCount: { type: `count`,
      title: 'Nb Zones Géographiques'
     },
  },

  dimensions: {
    geographicalAreaSK: {
      sql: `GeographicalAreaSK`,
      type: `number`,
      primaryKey: true,
    },
    geographicalAreaBK: {
      sql: `GeographicalAreaBK`,
      type: `number`,
      title: `ID Zone`,
    },
    geographicalAreaLabel: {
      sql: `GeographicalAreaLabel`,
      type: `string`,
      title: `Zone Géographique`,
    },
   
  },

  refreshKey: {
    every: `24 hours`,
  },
});


// ── DimWarehouse ─────────────────────────────────────────────

cube(`DimWarehouse`, {
  sql_table: `gold.dim_warehouse`,

  measures: {
    warehouseCount: { 
      type: `count`,
       title: `Nb Entrepôts`
     },
  },

  dimensions: {
    warehouseSK: {
      sql: `WarehouseSK`,
      type: `number`,
      primaryKey: true,
    },
    warehouseBK: {
      sql: `WarehouseBK`,
      type: `number`,
      title: `ID Entrepôt`,
    },
    warehouseCode: {
      sql: `WarehouseCode`,
      type: `string`,
      title: `Code Entrepôt`,
    },
    warehouseName: {
      sql: `WarehouseName`,
      type: `string`,
      title: `Entrepôt`,
    },
   
  },

  refreshKey: {
    every: `24 hours`,
  },
});