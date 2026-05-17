import requests
import sqlite3

SUPERSET_URL = "http://localhost:8088"
CUBEJS_URL   = "http://cubejs:4000"
CUBEJS_TOKEN = "sagap_cube_secret_2024_pfe_decisonnel_open_source"
DATASET_ID   = 3
DB_PATH      = "/app/superset_home/superset.db"

# Mesures countDistinct — mapping obligatoire car Cube.js valide le type
COUNT_DISTINCT_MAP = {
    "totalOrders"          : "COUNT(DISTINCT documentCode)",
    "totalActiveClients"   : "COUNT(DISTINCT CASE WHEN isActive = 1 THEN clientSK END)",
    "totalInactiveClients" : "COUNT(DISTINCT CASE WHEN isActive = 0 THEN clientSK END)",
    # nbArticlesMarge15 et nbDocsRemise20 → gérés par Cube directement
}

def build_expression(name, agg_type):
    if name in COUNT_DISTINCT_MAP:
        return COUNT_DISTINCT_MAP[name]
    if agg_type == "avg":
        return f"AVG({name})"
    elif agg_type == "countDistinct":
        return f"COUNT(DISTINCT {name})"  
    # Superset enverra SUM(nbArticlesMarge15) → Cube traduit lui-même
    else:
        return f"SUM({name})"
def clean_title(title, cube_name):
    # Supprimer le préfixe du cube dans le titre
    # Ex: "Fact Sales CA Total HT" → "CA Total HT"
    # Ex: "Dim Client Nombre de Clients" → "Nombre de Clients"
    import re
    # Convertir le nom du cube en mots (FactSales → Fact Sales)
    cube_words = re.sub(r'([A-Z])', r' \1', cube_name).strip()
    title_clean = title.replace(cube_words, "").strip()
    return title_clean if title_clean else title

def get_cube_measures():
    print("Lecture Cube.js (extended)...")
    resp = requests.get(
        f"{CUBEJS_URL}/cubejs-api/v1/meta?extended=true",
        headers={"Authorization": f"Bearer {CUBEJS_TOKEN}"},
        timeout=30
    )
    resp.raise_for_status()
    measures = []
    seen = set()
    for cube in resp.json().get("cubes", []):
        for m in cube.get("measures", []):
            n = m["name"].split(".")[-1]
            if n in seen or n == "count":
                continue
            seen.add(n)
            measures.append({
            "short_name": n,
            "title"     : clean_title(m.get("title", n), cube["name"]),
            "cube"      : cube["name"],
            "aggType"   : m.get("aggType", "sum"),
        })
    print(f"   {len(measures)} mesures trouvees")
    return measures

def main():
    print("=" * 55)
    print("  SAGAP - Synchronisation Cube.js -> Superset")
    print("=" * 55)

    measures      = get_cube_measures()
    measure_names = {m["short_name"] for m in measures}
    session       = requests.Session()

    print("Authentification Superset...")
    resp = session.post(f"{SUPERSET_URL}/api/v1/security/login",
        json={"username":"admin","password":"admin123","provider":"db","refresh":True},
        timeout=30)
    resp.raise_for_status()
    access_token = resp.json()["access_token"]

    csrf = session.get(f"{SUPERSET_URL}/api/v1/security/csrf_token/",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30).json()["result"]

    hdrs = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type" : "application/json",
        "X-CSRFToken"  : csrf,
        "Referer"      : f"{SUPERSET_URL}/tablemodelview/list/"
    }
    print("   OK")

    # ── Step 1 : Suppression métriques uniquement ─────────────
    # Les colonnes calculées sont préservées !
    print("Suppression metriques existantes...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM sql_metrics WHERE table_id=?", (DATASET_ID,))
    
    # Supprimer uniquement les colonnes NON calculées (expression NULL)
    conn.execute("""
        DELETE FROM table_columns 
        WHERE table_id=? 
        AND (expression IS NULL OR expression = '{}')
    """, (DATASET_ID,))
    conn.commit()
    conn.close()
    print("   OK - colonnes calculees preservees")

    # ── Step 2 : Créer les métriques ──────────────────────────
    print("\nCreation des metriques...")
    all_metrics = [{
        "metric_name" : "count",
        "verbose_name": "Nb Lignes",
        "metric_type" : "count",
        "expression"  : "COUNT(*)",
        "d3format"    : None,
        "warning_text": None,
    }]

    for m in measures:
        n    = m["short_name"]
        expr = build_expression(n, m["aggType"])
        all_metrics.append({
            "metric_name" : n,
            "verbose_name": m["title"],
            "metric_type" : m["aggType"],
            "expression"  : expr,
            "description" : f"Cube.js - {m['cube']} - aggType: {m['aggType']}",
            "d3format"    : None,
            "warning_text": None,
        })
        print(f"   + {n} ({m['aggType']}) -> {expr}")

    print(f"\nTotal: {len(all_metrics)} metriques")

    resp = session.put(
        f"{SUPERSET_URL}/api/v1/dataset/{DATASET_ID}",
        headers=hdrs,
        json={"metrics": all_metrics},
        timeout=30
    )
    print(f"Status metriques: {resp.status_code}")
    if resp.status_code == 200:
        print("OK - Metriques creees!")
    else:
        print(resp.text)
        return

    # ── Step 3 : Refresh colonnes depuis source ───────────────
    print("Refresh colonnes depuis source...")
    resp_refresh = session.put(
        f"{SUPERSET_URL}/api/v1/dataset/{DATASET_ID}/refresh",
        headers=hdrs, timeout=30
    )
    print(f"   Refresh status: {resp_refresh.status_code}")

    # Step 4 : Supprimer les colonnes mesures après refresh
    # Step 4 : Supprimer les colonnes mesures après refresh
    print("Suppression colonnes mesures...")
    conn = sqlite3.connect(DB_PATH)

    # Ajouter 'count' qui est exclu de measure_names mais doit être masqué
    all_measure_cols = measure_names | {"count"}

    placeholders = ','.join(['?' for _ in all_measure_cols])
    conn.execute(
        f"DELETE FROM table_columns WHERE table_id=? AND column_name IN ({placeholders})",
        [DATASET_ID] + list(all_measure_cols)
    )
    conn.commit()
    conn.close()
    print(f"   OK - {len(all_measure_cols)} colonnes supprimees!")

    print("=" * 55)
    print("  Synchronisation terminee avec succes!")
    print("=" * 55)

if __name__ == "__main__":
    main()