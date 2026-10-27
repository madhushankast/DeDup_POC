# Apparel Material Deduplication & Master Catalog System

A scalable, high-performance deduplication, fuzzy clustering, and master material catalog generation pipeline for apparel raw materials, featuring SQL relational ingestion and an interactive Streamlit dashboard.

---

## Architecture & Pipeline Overview

The pipeline processes 100k+ apparel catalog records across sequential stages, eliminating quadratic $O(N^2)$ comparisons through deterministic token-normalization, candidate blocking, Disjoint Set Union (DSU) graph clustering, and category isolation:

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

## Directory Structure

```text
POC_Dedup/
│
├── config/
│   ├── prefixes.yaml                     # Category-specific master code prefix mappings (e.g. FAB, TRM, THD)
│   └── splink_rules.yaml                 # Fuzzy match threshold configuration (threshold >= 0.85)
│
├── data/
│   ├── 01_raw/                           # Immutable incoming raw catalog
│   │   └── raw_materials.csv
│   ├── 02_by_category/                   # Category-partitioned files
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
├── scripts/
│   └── deduplicate_and_load.py           # Single self-contained SQL pipeline script (Extract, Deduplicate, Ingest)
│
├── app.py                                # Interactive Streamlit dashboard
├── .env.example                          # Database connection template
├── .env                                  # Local database credentials (ignored by git)
├── .gitignore                            # Environment & temporary cache rules
├── requirements.txt                      # Project dependencies
└── README.md                             # Documentation
```

---

## Quickstart & Running Steps

### 1. Environment Setup

1. **Activate Virtual Environment**:
   - **Windows (PowerShell):**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Database Connection (`.env`)**:
   Create a `.env` file in the project root (or copy from `.env.example`):
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/postgres

   # Or individual parameters:
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=YOUR_PASSWORD
   ```

---

### 2. Database Preparation (PostgreSQL / pgAdmin)

If you haven't yet imported the raw materials CSV into PostgreSQL:

1. Open pgAdmin Query Tool connected to your target database (e.g., `postgres`).
2. Run the DDL to create the raw staging table:
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
   ```
3. Import the CSV:
   - **Via SQL `COPY`:**
     ```sql
     COPY raw_materials FROM 'D:/Projects/2026.10.22 POC_Dedup/data/01_raw/raw_materials.csv'
     WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
     ```
   - **Or via pgAdmin GUI:** Right-click table `raw_materials` $\rightarrow$ **Import/Export Data...** $\rightarrow$ select file and click **OK**.

---

### 3. Run Option A: Automated SQL Pipeline Script

To extract raw records from PostgreSQL, perform fuzzy deduplication, generate standard master codes, and write normalized relational tables (`master_materials` and `material_records_mapped`) back into the database:

```powershell
.venv\Scripts\python.exe scripts\deduplicate_and_load.py

# Or
python scripts\deduplicate_and_load.py
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

### 4. Run Option B: Interactive Streamlit Web Dashboard

Launch the web dashboard to visualize catalog statistics, category distributions, UOM breakdowns, and inspect duplicate clusters:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

* Opens automatically at: **`http://localhost:8501`**
* **Features:**
  - **Raw Materials Overview:** KPI summary cards, Category bar charts, UOM donut distribution, Top 10 Colours, category filter, text search, and filtered CSV export.
  - **Master Catalog Explorer:** Redundancy reduction rate, cluster distribution, and drill-down into master codes to inspect mapped variants.

---

### 5. Run Option C: Sequential Jupyter Notebooks

If you prefer exploring step-by-step logic and generating CSV partition exports:

1. **`notebooks/01_partition_by_category.ipynb`**: Partitions raw catalog data by category to avoid cross-domain false positives.
2. **`notebooks/02_deduplicate_and_assign_codes.ipynb`**: Performs candidate blocking, RapidFuzz scoring, Union-Find clustering, and generates curated datasets.
3. **`notebooks/03_unique_materials_master.ipynb`**: Extracts 1 canonical row per unique master code.
4. **`notebooks/04_analysis_dashboard.ipynb`**: Comprehensive quality audit, score distributions, and interactive widget explorer.

---

## Deduplication Pipeline Results

| Category | Input Raw Records | Formed Clusters / Masters | Duplicate Rows Resolved | Redundancy Reduction |
| :--- | :---: | :---: | :---: | :---: |
| **Fabric** | 40,004 | 84 | 39,920 | 99.79% |
| **Trim** | 22,002 | 66 | 21,936 | 99.70% |
| **Thread** | 14,001 | 33 | 13,968 | 99.76% |
| **Label** | 12,001 | 32 | 11,969 | 99.73% |
| **Packaging** | 10,001 | 31 | 9,970 | 99.69% |
| **Uncategorized** | 2,002 | 86 | 1,916 | 95.70% |
| **TOTAL** | **100,011** | **332** | **99,679** | **99.67%** |
