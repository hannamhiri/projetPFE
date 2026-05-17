view(`SalesView`, {
  cubes: [
    {
      join_path: FactSales,
      includes: `*`
    },
    {
      join_path: FactSales.DimClient, // joindre DimClient via la relation définie dans FactSales.js
      includes: `*`
    },
    {
      join_path: FactSales.DimItem,
      includes: `*`
    },
    {
      join_path: FactSales.DimDate,
      includes: `*`
    },
    {
      join_path: FactSales.DimDocumentStatus,
      includes: `*`
    },
    {
      join_path: FactSales.DimDocumentType,
      includes: `*`
    },
    {
      join_path: FactSales.DimGeographicalArea,
      includes: `*`
    },
    {
      join_path: FactSales.DimWarehouse,
      includes: `*`
    },
  ]
});