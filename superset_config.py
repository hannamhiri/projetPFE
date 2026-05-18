# ============================================================
# Superset Override Config — Palette SAGAP Custom
# ============================================================

EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "sagap_blue",
        "description": "Palette SAGAP Custom",
        "label": "SAGAP Blue",
        "isDefault": True,
        "colors": [
            "#284E7B",  # bleu marine foncé
            "#659ABD",  # bleu moyen
            "#ADD4F3",  # bleu clair
            "#EFF3F5",  # gris bleuté très clair
            "#8F908D",  # gris neutre
            "#1a3a5c",  # bleu nuit profond
            "#4a7fa8",  # bleu acier
            "#c8e6f5",  # bleu pâle doux
            "#3d6b96",  # bleu intermédiaire
            "#7ab2d4",  # bleu azur doux
            "#2c5f8a",  # bleu professionnel
            "#b8cfe0",  # bleu grisé pâle
        ],
    }
]

EXTRA_SEQUENTIAL_COLOR_SCHEMES = [
    {
        "id": "sagap_sequential_blue",
        "description": "Séquentiel SAGAP Custom",
        "label": "SAGAP Sequential Blue",
        "isDiverging": False,
        "isDefault": True,
        "colors": [
            "#EFF3F5",  # très clair
            "#c8e6f5",
            "#ADD4F3",  # bleu clair
            "#7ab2d4",
            "#659ABD",  # bleu moyen
            "#4a7fa8",
            "#3d6b96",
            "#284E7B",  # bleu foncé
            "#1a3a5c",  # bleu nuit
        ],
    }
]

CUSTOM_CSS = """
.dashboard-content, .dashboard-grid, .grid-content, .grid-container,
.ant-tabs-content, .ant-tabs-content-top, .ant-tabs-content-holder,
.ant-tabs-tabpane, .ant-tabs-tabpane-active { background: #EFF3F5 !important; }

.dragdroppable, .dragdroppable-row, .grid-row,
.background--transparent, .resizable-container {
  background: transparent !important; border: none !important; box-shadow: none !important;
}

.dragdroppable-column {
  background: #ffffff !important;
  border: 1px solid #c8dcea !important;
  border-radius: 16px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(40,78,123,0.07) !important;
  overflow: hidden !important;
  transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s !important;
}

.dragdroppable-column:hover {
  border-color: rgba(101,154,189,0.5) !important;
  box-shadow: 0 8px 28px rgba(40,78,123,0.12) !important;
  transform: translateY(-1px) !important;
}

.chart-slice, .slice_container, .dashboard-component-chart-holder, .dashboard-chart {
  background: transparent !important; border: none !important;
  border-radius: 0 !important; box-shadow: none !important; transform: none !important;
}

.header-controls {
  background: transparent !important;
  border-bottom: 1px solid #EFF3F5 !important;
  padding: 14px 18px 11px !important;
}

.header-title {
  color: #284E7B !important; font-size: 11px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.12em !important;
}

.anchor-link-container, .header-controls .ant-dropdown-trigger, .anticon-ellipsis {
  opacity: 0 !important; transition: opacity 0.2s !important;
}

.dragdroppable-column:hover .anchor-link-container,
.dragdroppable-column:hover .ant-dropdown-trigger,
.dragdroppable-column:hover .anticon-ellipsis {
  opacity: 1 !important; color: #8F908D !important;
}

.superset-legacy-chart-big-number, .big_number_total, .big_number, .no-trendline {
  background: transparent !important;
}

.header-line {
  background: linear-gradient(135deg, #284E7B 0%, #659ABD 100%) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  font-weight: 800 !important; letter-spacing: -1.5px !important;
}

.kicker {
  color: #8F908D !important; font-size: 10.5px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.1em !important;
}

.subheader-line { color: #8F908D !important; font-size: 11.5px !important; }

.positive {
  color: #059669 !important; font-weight: 700 !important;
  background: rgba(5,150,105,0.08) !important;
  padding: 1px 6px !important; border-radius: 4px !important;
}

.superset-chart-table .table, .table.table-striped, .table.table-condensed {
  background: transparent !important; border: none !important; font-size: 12px !important;
}

.superset-chart-table .table thead th,
.table.table-striped thead th, .table.table-condensed thead th {
  background: #EFF3F5 !important; color: #284E7B !important;
  font-size: 10px !important; font-weight: 800 !important;
  text-transform: uppercase !important; letter-spacing: 0.09em !important;
  border-bottom: 2px solid #ADD4F3 !important; border-top: none !important;
  padding: 10px 13px !important; white-space: nowrap !important;
}

.superset-chart-table .table tbody td:first-child,
.table.table-striped tbody td:first-child {
  color: #284E7B !important; font-weight: 600 !important;
}

.superset-chart-table .table tbody td,
.table.table-striped tbody td, .table.table-condensed tbody td {
  color: #3d6b96 !important; border-bottom: 1px solid #EFF3F5 !important;
  border-top: none !important; padding: 9px 13px !important;
}

.table.table-striped > tbody > tr:nth-of-type(odd) > td { background: #f7fafc !important; }
.table.table-striped tbody tr:hover td,
.superset-chart-table .table tbody tr:hover td { background: #ADD4F3 !important; }

.dashboard-markdown {
  background: linear-gradient(180deg, #284E7B 0%, #1a3a5c 100%) !important;
  border-radius: 14px !important; padding: 8px 6px !important;
}

.dashboard-markdown .text-container, .dashboard-markdown p,
.dashboard-markdown span, .dashboard-markdown a, .dashboard-markdown div {
  color: #ADD4F3 !important; font-size: 10.5px !important; font-weight: 600 !important;
  text-align: center !important; text-decoration: none !important;
}

.dashboard-markdown a:hover, .dashboard-markdown p:hover { color: #EFF3F5 !important; }

.form-inline {
  background: #ffffff !important; border: 1px solid #c8dcea !important;
  border-radius: 12px !important; padding: 8px 18px !important;
  box-shadow: 0 1px 4px rgba(40,78,123,0.05) !important;
}

.form-inline label, .dt-global-filter label {
  color: #284E7B !important; font-size: 10.5px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.08em !important;
}

.form-inline .ant-input, .ant-input.ant-input-outlined {
  background: #EFF3F5 !important; border: 1px solid #ADD4F3 !important;
  border-radius: 7px !important; color: #284E7B !important;
}

.right-border-only { border-right: 1px solid #c8dcea !important; }
.anticon-table, .anticon-down, .anticon-minus-circle { color: #8F908D !important; }

.dragdroppable-drop-indicator {
  background: rgba(40,78,123,0.07) !important;
  border: 2px dashed rgba(101,154,189,0.4) !important; border-radius: 10px !important;
}

.chart-container::-webkit-scrollbar,
.slice_container::-webkit-scrollbar { width: 4px; height: 4px; }
.chart-container::-webkit-scrollbar-track,
.slice_container::-webkit-scrollbar-track { background: #EFF3F5; }
.chart-container::-webkit-scrollbar-thumb,
.slice_container::-webkit-scrollbar-thumb { background: #ADD4F3; border-radius: 2px; }
.chart-container::-webkit-scrollbar-thumb:hover,
.slice_container::-webkit-scrollbar-thumb:hover { background: #284E7B; }
"""