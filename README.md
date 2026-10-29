# Apparel Material Deduplication & Master Catalog System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.10+-FFF000.svg)](https://duckdb.org/)
[![RapidFuzz](https://img.shields.io/badge/RapidFuzz-3.0+-green.svg)](https://github.com/rapidfuzz/RapidFuzz)

A scalable, high-performance deduplication, fuzzy clustering, and master material catalog generation pipeline for apparel raw materials, featuring SQL relational ingestion and an interactive Streamlit dashboard.

---

## Architecture & Pipeline Overview

The pipeline processes 100k+ apparel catalog records across sequential stages, eliminating quadratic $\mathcal{O}(N^2)$ comparisons through deterministic token-normalization, candidate blocking, Disjoint Set Union (DSU) graph clustering, and category isolation:

```text
[PostgreSQL / CSV] Raw Materials (100,011 rows)
       │
       ▼  Step 1: Partitioning & Category Isolation
Category-Isolated Partitions (Fabric, Trim, Thread, Label, Packaging, Uncategorized)
       │
       ▼  Step 2: RapidFuzz Similarity & Union-Find Graph Clustering (Threshold >= 0.85)
Identifies Connected Duplicate Clusters & Formats Standard Master Codes (e.g., FAB-000001)
       │
       ▼  Step 3: Relational Normalization & SQL Ingestion (with Foreign Key Constraints)
Table A: master_materials (Parent Entity - 332 canonical items)
Table B: material_records_mapped (Child Tracking Entity - 100,011 items with is_duplicate & FK)
       │
       ▼  Step 4: Interactive Web & Analytics Dashboard
Streamlit Dashboard (http://localhost:8501) & Jupyter Notebook Suite
```

---

## Deduplication Pipeline Results

Across 100,011 raw catalog rows, the pipeline resolved **99,679 redundant records**, synthesizing them into **332 canonical master codes** with an overall **99.67% redundancy reduction**.

| Category | Input Raw Records | Formed Clusters / Masters | Duplicate Rows Resolved | Redundancy Reduction |
| :--- | :---: | :---: | :---: | :---: |
| **Fabric** | 40,004 | 84 | 39,920 | 99.79% |
| **Trim** | 22,002 | 66 | 21,936 | 99.70% |
| **Thread** | 14,001 | 33 | 13,968 | 99.76% |
| **Label** | 12,001 | 32 | 11,969 | 99.73% |
| **Packaging** | 10,001 | 31 | 9,970 | 99.69% |
| **Uncategorized** | 2,002 | 86 | 1,916 | 95.70% |
| **TOTAL** | **100,011** | **332** | **99,679** | **99.67%** |

### Analytics & Visualizations

<p align="center">
  <img src="reports/figures/funnel_chart.png" alt="Deduplication Funnel Chart" width="700"/>
</p>

<p align="center">
  <img src="reports/figures/before_after_chart.png" alt="Before vs After Catalog Volume" width="700"/>
</p>

---

## Directory Structure

```text
POC_Dedup/
│
├── .devcontainer/                        # VS Code Remote Containers & GitHub Codespaces config
│   └── devcontainer.json
│
├── config/
│   ├── prefixes.yaml                     # Category-specific master code prefix mappings (FAB, TRM, etc.)
│   └── splink_rules.yaml                 # Fuzzy match threshold configuration (threshold >= 0.85)
│
├── data/
│   ├── 01_raw/                           # Immutable incoming raw catalog
│   │   └── raw_materials.csv
│   ├── 02_by_category/                   # Category-partitioned CSVs
│   ├── 03_clusters/                      # Intermediate clustered partitions
│   ├── 04_curated/                       # Curated category datasets with cluster metrics
│   ├── 05_unique/                        # Canonical master materials (1 row per master code)
│   └── overviews/                        # Category partition summary reports
│
├── notebooks/                            # Interactive step-by-step Jupyter notebooks
│   ├── 01_partition_by_category.ipynb
│   ├── 02_deduplicate_and_assign_codes.ipynb
│   ├── 03_unique_materials_master.ipynb
│   └── 04_analysis_dashboard.ipynb
│
├── reports/
│   └── figures/                          # Visualization charts and pipeline metrics
│
├── scripts/
│   └── deduplicate_and_load.py           # Self-contained SQL pipeline (Extract, Deduplicate, Ingest)
│
├── app.py                                # Interactive Streamlit dashboard
├── .env.example                          # Database connection template
├── .gitignore                            # Git exclusion rules
├── requirements.txt                      # Project dependencies
└── README.md                             # Project documentation
```

---

## Quickstart Guide

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/madhushankast/DeDup_POC.git
cd DeDup_POC

# Create and activate virtual environment
# Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Database (Optional for SQL Pipeline)

Create a `.env` file in the project root (reference `.env.example`):

```ini
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/postgres

# Or Supabase / Remote PostgreSQL Pooler URI:
# DATABASE_URL=postgresql+psycopg2://postgres.[REF]:[PASS]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

---

## Execution Modes

### Mode 1: Interactive Streamlit Web Dashboard

Launch the web app to explore the raw catalog, inspect duplicate clusters, and view real-time metrics:

```bash
streamlit run app.py
```
- Available at: **`http://localhost:8501`**
- **Capabilities:**
  - **Raw Materials Overview**: KPI summary cards, Category bar charts, UOM distribution, filterable tables, and CSV export.
  - **Master Catalog Explorer**: Redundancy reduction rates, cluster breakdown, and item variant drill-downs.

---

### Mode 2: Automated End-to-End Pipeline Script

Extract raw records from PostgreSQL, perform fuzzy deduplication, assign canonical master codes, and write normalized relational tables (`master_materials` and `material_records_mapped`):

```bash
python scripts/deduplicate_and_load.py
```

* **CLI Options:**
  - `--threshold 0.85`: Set string similarity threshold (default: `0.85`).
  - `--source-table raw_materials`: Custom source table name.
  - `--db-url "postgresql+psycopg2://user:pass@localhost:5432/dbname"`: Override connection string.
  - `--db-url "sqlite:///data/materials.db"`: Offline SQLite execution.

* **Database Output Schema Created:**
  - `master_materials`: Parent entity with `new_master_code` (PRIMARY KEY), `canonical_material_name`, `category`, and `cluster_record_count`.
  - `material_records_mapped`: Child tracking entity with `material_item_code` (PRIMARY KEY), foreign key `new_master_code REFERENCES master_materials(new_master_code) ON DELETE CASCADE`, `is_duplicate` flag, and `similarity_score`.

---

### Mode 3: Sequential Jupyter Notebooks

For interactive research and exploratory data analysis:

1. **`notebooks/01_partition_by_category.ipynb`**: Partitions raw catalog data by category to prevent cross-domain false matches.
2. **`notebooks/02_deduplicate_and_assign_codes.ipynb`**: Executes candidate blocking, RapidFuzz scoring, and Union-Find clustering.
3. **`notebooks/03_unique_materials_master.ipynb`**: Generates 1 canonical row per unique master code.
4. **`notebooks/04_analysis_dashboard.ipynb`**: Audits match quality, score distributions, and cluster cohesion.

---

## Staging Table DDL (PostgreSQL)

If loading `raw_materials.csv` manually via PostgreSQL / pgAdmin:

```sql
CREATE TABLE IF NOT EXISTS raw_materials (
    material_code             VARCHAR(50),
    material_name             VARCHAR(255),
    category                  VARCHAR(100),
    composition               VARCHAR(255),
    construction_spec         VARCHAR(255),
    colour                    VARCHAR(100),
    width_size                VARCHAR(100),
    gsm                       VARCHAR(50),
    inventory_uom             VARCHAR(50)
);

-- Copy command (replace with your local absolute path):
-- COPY raw_materials FROM '/path/to/data/01_raw/raw_materials.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
```
