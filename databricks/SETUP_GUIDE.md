# Databricks Database Setup Guide (Tamil + English)

Live data illa — **neenga Databricks-la tables create panni, data feed pannanum**. Ippo project-ku ellaa files ready.

---

## Enna tool use pannanum? (Which tool to view tables?)

| Tool | Use | Link |
|------|-----|------|
| **Databricks SQL Editor** | Tables create, data insert, SELECT query | Workspace → **SQL** → **SQL Editor** |
| **Catalog Explorer** | Tables list paaka, schema browse | Workspace → **Catalog** (left menu) |
| **Databricks Notebook** | Python/SQL run pannalam | Workspace → **New** → **Notebook** |

**Best for beginners:** **SQL Editor** — tables create pannalam, data paakalam, query run pannalam.

---

## Step-by-step

### Step 1: Databricks account

1. [Databricks Free Edition](https://www.databricks.com/learn/free-edition) sign up
2. Workspace open pannunga

### Step 2: SQL Warehouse create pannunga

1. Left menu → **SQL** → **SQL Warehouses**
2. **Create SQL Warehouse** (Starter size is enough for POC)
3. Warehouse ID copy pannunga (URL-la irukkum, e.g. `a1b2c3d4e5f6g7h8`)

### Step 3: Access Token generate pannunga

1. Top-right profile → **Settings** → **Developer** → **Access tokens**
2. **Generate new token** → copy token

### Step 4: Tables create pannunga (SQL Editor)

1. **SQL** → **SQL Editor**
2. Warehouse select pannunga
3. File open pannunga: `databricks/sql/01_create_tables.sql`
4. Full SQL copy-paste pannitu **Run** click pannunga

**3 tables create aagum:**

| Table | Purpose |
|-------|---------|
| `workspace.dataops_copilot.pipeline_runs` | Pipeline status |
| `workspace.dataops_copilot.failure_logs` | Failure diagnosis |
| `workspace.dataops_copilot.cluster_metrics` | Optimization data |

### Step 5: Tables paathu confirm pannunga

SQL Editor-la run pannunga:

```sql
SHOW TABLES IN workspace.dataops_copilot;

SELECT * FROM workspace.dataops_copilot.pipeline_runs;
SELECT * FROM workspace.dataops_copilot.failure_logs;
SELECT * FROM workspace.dataops_copilot.cluster_metrics;
```

**Or** Catalog Explorer-la:
`main` → `dataops_copilot` → tables click pannunga

### Step 6: Data feed pannunga (seed script)

`.env` file update pannunga:

```env
USE_DATABRICKS=true
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your_token_here
DATABRICKS_WAREHOUSE_ID=your_warehouse_id_here
DATABRICKS_CATALOG=workspace
DATABRICKS_SCHEMA=dataops_copilot
```

Terminal-la run pannunga:

```powershell
cd c:\Users\Gobi\Desktop\madhu\dataops-copilot
py scripts/seed_databricks.py
```

Idhu JSON mock data-a Databricks tables-la insert pannum (10 pipelines, 5 failures, 6 clusters).

### Step 7: Flask app connect pannunga

```powershell
cd backend
py app.py
```

Check pannunga: **http://localhost:5000/databricks/status**

Dashboard-la **"Databricks Live"** badge kaanum.

---

## Architecture

```
Databricks Tables (pipeline_runs, failure_logs, cluster_metrics)
        ↓ SQL API
Flask Backend (data_service.py)
        ↓
Gemini 2.5 Flash → AI answers
        ↓
SQLite (query_log only — audit trail)
```

---

## Files in this folder

| File | Purpose |
|------|---------|
| `sql/01_create_tables.sql` | CREATE TABLE scripts |
| `SETUP_GUIDE.md` | This guide |
| `../scripts/seed_databricks.py` | JSON data → Databricks insert |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Catalog 'main' was not found | Free Edition uses `workspace` — set `DATABRICKS_CATALOG=workspace` and re-run SQL |
| Table not found | Run `01_create_tables.sql` first |
| Warehouse not running | SQL Warehouses → Start warehouse |
| Permission denied | Token regenerate with SQL access |
| App shows Mock JSON | `USE_DATABRICKS=true` + warehouse ID in `.env` |
