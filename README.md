# Apparel Material Deduplication & Master Catalog System

A scalable, high-performance deduplication, fuzzy clustering, and master material catalog generation pipeline for apparel raw materials using interactive Jupyter Notebooks.

---

## Architecture & Pipeline Overview

The pipeline processes 100k+ apparel catalog records across 5 sequential stages, eliminating quadratic $O(N^2)$ comparisons through intelligent candidate blocking, Disjoint Set Union (DSU) graph clustering, and category isolation:

```text
[01_raw] Raw Materials Catalog (100,011 rows)
   │
   ▼  Step 1: Partitioning & Category Isolation (01_partition_by_category.ipynb)
[02_by_category] Category-Isolated Partitions (category_<slug>.csv)
   │
   ▼  Step 2: Candidate Blocking & DSU Fuzzy Clustering (02_deduplicate_and_assign_codes.ipynb)
[03_clusters] Clustered Partitions (clustered_<slug>.csv)
   │
   ▼  Step 2: Curated Record Export (02_deduplicate_and_assign_codes.ipynb)
[04_curated] Curated Datasets with Master Codes (curated_<slug>.csv)
   │
   ▼  Step 3: Unique Master Extraction (03_unique_materials_master.ipynb)
[05_unique] Canonical Unique Master Catalogs (unique_master_<slug>.csv)
   │
   ▼  Step 4: Audit & Diagnostics (04_analysis_dashboard.ipynb)
Executive Quality, Funnel & Reduction Dashboard
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
│   │
│   ├── 02_by_category/                   # Step 1: Category-partitioned files
│   │   ├── category_fabric.csv
│   │   ├── category_label.csv
│   │   ├── category_packaging.csv
│   │   ├── category_thread.csv
│   │   ├── category_trim.csv
│   │   └── category_uncategorized.csv
│   │
│   ├── 03_clusters/                      # Step 2: Intermediate clustered partitions
│   │   ├── clustered_fabric.csv
│   │   ├── clustered_label.csv
│   │   ├── clustered_packaging.csv
│   │   ├── clustered_thread.csv
│   │   ├── clustered_trim.csv
│   │   └── clustered_uncategorized.csv
│   │
│   ├── 04_curated/                       # Step 2: Curated category datasets with cluster metrics
│   │   ├── curated_fabric.csv
│   │   ├── curated_label.csv
│   │   ├── curated_packaging.csv
│   │   ├── curated_thread.csv
│   │   ├── curated_trim.csv
│   │   └── curated_uncategorized.csv
│   │
│   ├── 05_unique/                        # Step 3: Canonical master materials (1 row per master code)
│   │   ├── unique_master_fabric.csv
│   │   ├── unique_master_label.csv
│   │   ├── unique_master_packaging.csv
│   │   ├── unique_master_thread.csv
│   │   ├── unique_master_trim.csv
│   │   └── unique_master_uncategorized.csv
│   │
│   └── overviews/                        # Category partition summary reports
│       ├── categories_overview.csv
│       └── category_uncategorized.csv
│
├── notebooks/                            # Interactive step-by-step workflow
│   ├── 01_partition_by_category.ipynb
│   ├── 02_deduplicate_and_assign_codes.ipynb
│   ├── 03_unique_materials_master.ipynb
│   └── 04_analysis_dashboard.ipynb
│
├── .gitignore                            # Environment & temporary cache rules
├── requirements.txt                      # Project dependencies
└── README.md                             # Documentation
```

---

## Setup & Installation

1. **Activate Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Sequential Notebook Workflow

Execute the notebooks sequentially in Jupyter, VS Code, or your preferred IDE:

### 1. `notebooks/01_partition_by_category.ipynb`
* **Objective:** Partition raw catalog data by category to avoid cross-category contamination.
* **Logic:**
  * Reads raw catalog data from `data/01_raw/raw_materials.csv`.
  * Standardizes category names into snake_case slugs (`Fabric` $\rightarrow$ `fabric`, `Packaging / Boxing` $\rightarrow$ `packaging_boxing`).
  * Generates separate category partitions in `data/02_by_category/category_<slug>.csv` and an overview table in `data/overviews/categories_overview.csv`.
  * Isolates uncategorized records into `category_uncategorized.csv` so zero rows are lost.

### 2. `notebooks/02_deduplicate_and_assign_codes.ipynb`
* **Objective:** Intra-category deduplication, candidate blocking, fuzzy clustering, and master item code assignment.
* **Strict Material-Name-Only Clustering:**
  * Clustering evaluates **strictly** `Material name`. The `Colour` column is never split, scored, or clustered upon, and no SKU/variant suffix codes (e.g. `FAB-000001-NAV`) are generated.
* **4-Stage Clustering Engine:**
  1. **Text Normalization:** Lowercase, standard symbol replacement (`×` $\rightarrow$ `x`, `&` $\rightarrow$ `and`, `%` $\rightarrow$ `percent`), punctuation stripping, and alphabetical token sorting.
  2. **Candidate Generation & Inverted Index Blocking:**
     * Category unique names $\le 600$: evaluates pairwise similarity directly.
     * Category unique names $> 600$: blocks on common tokens ($\ge 3$ characters) or first 4-character prefixes, plus string length filtering.
  3. **Similarity Scoring:** RapidFuzz Levenshtein / Token Sort similarity (fallback to `SequenceMatcher`) with threshold $\ge 0.85$.
  4. **Graph Clustering:** Disjoint Set Union (DSU / Union-Find) connected components.
* **Code & Flag Assignment:**
  * Assigns sequential category-scoped `cluster_id` starting from `1` per partition.
  * Formats `new_master_code` with the category prefix and a 6-digit zero pad (e.g., `FAB-000001`, `TRM-000001`).
  * Computes `similarity_score` relative to canonical cluster representative.
  * Computes `cluster_record_count` and sets `is_duplicate = (cluster_record_count > 1)`.
* **Exports:** Saves `data/03_clusters/clustered_<slug>.csv` and `data/04_curated/curated_<slug>.csv` containing:
  `Material/item code`, `Material name`, `norm_material_name`, `cluster_id`, `new_master_code`, `similarity_score`, `cluster_record_count`, `is_duplicate`.

### 3. `notebooks/03_unique_materials_master.ipynb`
* **Objective:** Extract unique canonical master items from curated category files into the final master catalog.
* **Key Requirements:**
  * Iterates over each `data/04_curated/curated_<slug>.csv` file independently (zero cross-category merging).
  * Collapses rows to **strictly 1 row per `new_master_code`**.
  * Identifies the canonical `norm_material_name` and display `Material name` (where `similarity_score == 1.0` or most frequent).
* **Strict 6-Column Export Schema:**
  * `new_master_code`
  * `norm_material_name`
  * `Material name`
  * `Category`
  * `cluster_id`
  * `cluster_record_count`
* **Output Destination:** Saved per category to `data/05_unique/unique_master_<slug>.csv`.

### 4. `notebooks/04_analysis_dashboard.ipynb`
* **Objective:** End-to-end interactive audit and analytics dashboard tracing duplicate resolution.
* **Dashboard Sections:**
  1. **Data Funnel & Compression:** Overall and per-category waterfall/shrinkage metrics from raw rows $\rightarrow$ partitions $\rightarrow$ normalized names $\rightarrow$ clusters $\rightarrow$ unique master items.
  2. **Category Isolation Impact:** Quantifies cross-category false positives prevented by stage 1 partitioning.
  3. **Text Normalization Trace:** Quantifies exact duplicates collapsed purely by token sorting and case/punctuation standardization.
  4. **Fuzzy Matching & Cluster Distribution:** Similarity score distributions, cluster size buckets, and top 5 largest clusters per category.
  5. **Transitive Chaining & Quality Audit:** Borderline match review ($0.85 \le \text{score} \le 0.88$), transitive chaining verification, and side-by-side variant inspections.
  6. **Final Master State & Integrity Checks:** Before vs. After validation table, schema conformity, and unique constraint assertions.
  7. **Interactive Category Explorer:** Interactive drill-down by category using `ipywidgets`.

---

## Deduplication Pipeline Results

| Category | Input Raw Records | Formed Clusters / Masters | Duplicate Rows Resolved | Reduction Rate |
| :--- | :---: | :---: | :---: | :---: |
| **Fabric** | 40,004 | 84 | 39,920 | 99.79% |
| **Trim** | 22,002 | 66 | 21,936 | 99.70% |
| **Thread** | 14,001 | 33 | 13,968 | 99.76% |
| **Label** | 12,001 | 32 | 11,969 | 99.73% |
| **Packaging** | 10,001 | 31 | 9,970 | 99.69% |
| **Uncategorized** | 2,002 | 86 | 1,916 | 95.70% |
| **TOTAL** | **100,011** | **332** | **99,679** | **99.67%** |
