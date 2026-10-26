# Apparel Item Deduplication System

A modular deduplication and master catalog generation workflow for apparel raw materials using interactive Jupyter Notebooks.

## Directory Structure

```text
POC_Dedup/
│
├── data/
│   ├── 01_raw/                      # Immutable incoming raw files
│   │   └── raw_materials.csv
│   │
│   ├── 02_by_category/              # Output from Step 1 (Partitioning)
│   │   ├── category_fabric.csv
│   │   ├── category_trim.csv
│   │   ├── category_thread.csv
│   │   ├── category_label.csv
│   │   └── category_packaging.csv
│   │
│   ├── overviews/                   # Summary metadata & distribution reports
│   │   ├── categories_overview.csv  # Valid categories distribution overview
│   │   ├── uncategorized_overview.csv # Summary statistics for uncategorized/missing records
│   │   └── uncategorized_records.csv  # Raw records isolated due to missing category
│   │
│   ├── 03_clusters/                 # Intermediate partition cluster files (CSV & Parquet)
│   │   ├── category_fabric_clusters.csv
│   │   ├── category_fabric_clusters.parquet
│   │   └── ...
│   │
│   └── 04_curated/                  # Final cleaned datasets & Master Catalog
│       ├── master_deduplicated_catalog.csv # Unified table with standardized item codes, SKUs & cluster metadata
│       └── duplicates_review_audit.csv     # Audit log of grouped duplicates for manual review
│
├── config/
│   ├── prefixes.yaml                # Item code prefix mapping per category
│   └── splink_rules.yaml            # Thresholds, blocking rules & similarity weights
│
├── notebooks/                       # Interactive step-by-step workflow
│   ├── 01_partition_by_category.ipynb
│   └── 02_deduplicate_and_assign_codes.ipynb
│
├── requirements.txt                 # Dependencies
└── README.md                        # Documentation
```

## Setup & Installation

1. **Activate Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Interactive Notebooks Workflow

Execute the notebooks sequentially in Jupyter, VS Code, or your preferred IDE:

1. **[01_partition_by_category.ipynb](file:///d:/Projects/POC_Dedup/notebooks/01_partition_by_category.ipynb)**
   - Loads the raw material catalog from `data/01_raw/raw_materials.csv`.
   - Cleans and normalizes category names into snake_case slugs.
   - Partitions the data into isolated category CSV files inside `data/02_by_category/` to guarantee zero cross-category contamination.

2. **[02_deduplicate_and_assign_codes.ipynb](file:///d:/Projects/POC_Dedup/notebooks/02_deduplicate_and_assign_codes.ipynb)**
   - Ingests valid categories from `data/overviews/categories_overview.csv` and scans corresponding partitions in `data/02_by_category/`.
   - Normalizes material names (lowercase, punctuation removal, symbol replacements, and alphabetical token sorting).
   - Computes pairwise string similarity scores strictly on `Material name` within each partition (threshold >= 0.85) and clusters matches using Union-Find / connected components.
   - Assigns category-prefixed Master Item Codes per cluster (e.g., `FAB-000001`).
   - Adds `similarity_score`, `cluster_id`, and `is_duplicate` columns.
   - Exports intermediate clustered partitions to `data/03_clusters/`, full dataset to `data/04_curated/master_deduplicated_catalog.csv`, and duplicate audit rows to `data/04_curated/duplicates_review_audit.csv`.
