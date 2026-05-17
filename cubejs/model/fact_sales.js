cube(`FactSales`, {
  sql_table: `gold.fact_sales`,
  

  joins: {
    DimClient: {
      sql: `${CUBE}.ClientSK = ${DimClient}.ClientSK`,
      relationship: `many_to_one`,
    },
    DimItem: {
      sql: `${CUBE}.ItemSK = ${DimItem}.ItemSK`,
      relationship: `many_to_one`,
    },
    DimDate: {
      sql: `toInt32(${CUBE}.DateSK) = ${DimDate}.DateSK`,
      relationship: `many_to_one`,
    },
    DimDocumentStatus: {
      sql: `${CUBE}.DocumentStatusSK = ${DimDocumentStatus}.DocumentStatusSK`,
      relationship: `many_to_one`,
    },
    DimDocumentType: {
      sql: `${CUBE}.DocumentTypeSK = ${DimDocumentType}.DocumentTypeSK`,
      relationship: `many_to_one`,
    },
    DimGeographicalArea: {
      sql: `${CUBE}.GeographicalAreaSK = ${DimGeographicalArea}.GeographicalAreaSK`,
      relationship: `many_to_one`,
    },
    DimWarehouse: {
      sql: `${CUBE}.WarehouseSK = ${DimWarehouse}.WarehouseSK`,
      relationship: `many_to_one`,
    },
  },

  measures: {

    // ── Comptages ─────────────────────────────────────────────
    count: {
      type: `count`,
      title: `Nb de Lignes`,
    },
    totalOrders: {
      sql: `DocumentCode`,
      type: `countDistinct`,
      title: `Nb Commandes`,
    },
    totalActiveClients: {
      sql: `CASE WHEN ${DimClient.isActive} = 1 THEN ${DimClient.clientSK} END`,
      type: `countDistinct`,
      title: `Nb Clients actifs`,
    },

    totalInactiveClients: {
      sql: `CASE WHEN ${DimClient.isActive} = 0 THEN ${DimClient.clientSK} END`,
      type: `countDistinct`,
      title: `Nb Clients inactifs`,
    },
    tauxChurn: {
      type: `number`,
      sql: `${totalInactiveClients} / nullIf(${totalActiveClients} + ${totalInactiveClients}, 0) * 100`,
      title: `Taux Churn (%)`
    },

    // ── CA ────────────────────────────────────────────────────
    totalPriceHT: {
      sql: `LinePrice`,
      type: `sum`,
      title: `CA Total HT`,
    },
    avgOrderValue: {
      sql: `${totalPriceHT} / nullIf(${totalOrders}, 0)`,
      type: `number`,
      title: `Panier Moyen`,
    },

    // ── CA segmenté ───────────────────────────────────────────
    totalPriceHTB2B: {
      sql: `CASE WHEN ${DimClient.isBTOB} = 1 THEN LinePrice ELSE 0 END`,
      type: `sum`,
      title: `CA B2B`,
    },
    totalPriceHTB2C: {
      sql: `CASE WHEN ${DimClient.isBTOB} = 0 THEN LinePrice ELSE 0 END`,
      type: `sum`,
      title: `CA B2C`,
    },
    totalPriceHTPos: {
      sql: `CASE WHEN IsForPos = 1 THEN LinePrice ELSE 0 END`,
      type: `sum`,
      title: `CA Point de Vente`,
    },
    totalPriceHTNonPos: {
      sql: `CASE WHEN IsForPos = 0 THEN LinePrice ELSE 0 END`,
      type: `sum`,
      title: `CA Hors POS`,
    },

    // ── Coût & Marge ──────────────────────────────────────────
    totalCostPrice: {
      sql: `CostPrice`,
      type: `sum`,
      title: `Coût Total`,
    },
    grossMargin: {
      sql: `${totalPriceHT} - ${totalCostPrice}`,
      type: `number`,
      title: `Marge Brute`,
    },
    grossMarginRate: {
      sql: `CASE WHEN ${totalPriceHT} = 0 THEN 0 
            ELSE (${totalPriceHT} - ${totalCostPrice}) / ${totalPriceHT} * 100 
            END`,
      type: `number`,
      title: `Taux de Marge (%)`,
    },
    

    // ── Quantité ──────────────────────────────────────────────
    totalQuantity: {
      sql: `Quantity`,
      type: `sum`,
      title: `Quantité Totale`,
    },
    avgQuantity: {
      sql: `Quantity`,
      type: `avg`,
      title: `Quantité Moyenne`,
    },

    // ── Remise ────────────────────────────────────────────────
    totalDiscount: {
      sql: `DiscountAmount`,
      type: `sum`,
      title: `Remise Totale`,
    },
    avgDiscountRate: {
      sql: `DiscountPercentage`,
      type: `avg`,
      title: `Remise Moyenne (%)`,
    },
    avgDiscountRateB2B: {
      sql: `CASE WHEN ${DimClient.isBTOB} = 1 THEN DiscountPercentage END`,
      type: `avg`,
      title: `Remise Moyenne B2B (%)`,
    },
    avgDiscountRateB2C: {
      sql: `CASE WHEN ${DimClient.isBTOB} = 0 THEN DiscountPercentage END`,
      type: `avg`,
      title: `Remise Moyenne B2C (%)`,
    },
    //-------- for alerts
    // ---- for alerts
    nbArticlesMarge15: {
      type: `countDistinct`,
      sql: `CASE 
        WHEN (LinePrice - CostPrice) / nullIf(LinePrice, 0) * 100 < 15 
        THEN ItemSK 
      END`,
      title: `Nb articles marge < 15%`
    },

    nbDocsRemise20: {
      type: `countDistinct`,
      sql: `CASE 
        WHEN DiscountPercentage > 20 
        THEN DocumentCode 
      END`,
      title: `Nb docs remise > 20%`
    },
    nbDocsVenteAPerte: {
      type: `countDistinct`,
      sql: `CASE WHEN CostPrice > LinePrice THEN DocumentCode END`,
      title: `Nb docs vente à perte`
    },
  },

  dimensions: {

    // ── Primary Key ───────────────────────────────────────────
    pk: {
      sql: `concat(
        toString(${CUBE}.ClientSK), '_',
        toString(${CUBE}.ItemSK), '_',
        toString(${CUBE}.DocumentStatusSK), '_',
        toString(${CUBE}.DocumentTypeSK), '_',
        toString(${CUBE}.GeographicalAreaSK), '_',
        toString(${CUBE}.WarehouseSK), '_',
        toString(coalesce(${CUBE}.DateSK, 0)), '_',
        toString(coalesce(${CUBE}.DocumentCode, ''))
      )`,
      type: `string`,
      primaryKey: true,
    },

    // ── Attributs dégénérés ───────────────────────────────────
    documentCode: {
      sql: `DocumentCode`,
      type: `string`,
      title: `Code Document`,
    },
    isForPos: {
      sql: `IsForPos`,
      type: `number`,
      title: `Point de Vente`,
    },
   
   
  },

  refreshKey: {
    sql: `SELECT MAX(DateSK) FROM gold.fact_sales`,
  },
});