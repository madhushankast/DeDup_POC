"""
Apparel Material Deduplication & Relational Normalization Pipeline
Role: Senior Data & Database Engineer

This self-contained script extracts raw materials from an SQL database (PostgreSQL or SQLite),
normalizes and deduplicates records strictly based on `Material name` within category partitions,
generates standardized master codes (e.g. FAB-000001), and ingests normalized parent/child
relational tables with strict foreign key constraints back into the database.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from dotenv import load_dotenv

# Try importing SQLAlchemy; fallback gracefully if needed
try:
    import sqlalchemy as sa
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# Try RapidFuzz; fallback to difflib
try:
    from rapidfuzz.distance import Levenshtein as rf_levenshtein
    from rapidfuzz import fuzz as rf_fuzz
    def compute_string_similarity(s1: str, s2: str) -> float:
        if s1 == s2:
            return 1.0
        return max(float(rf_levenshtein.normalized_similarity(s1, s2)), rf_fuzz.token_sort_ratio(s1, s2) / 100.0)
    FUZZY_ENGINE = "RapidFuzz"
except ImportError:
    import difflib
    def compute_string_similarity(s1: str, s2: str) -> float:
        if s1 == s2:
            return 1.0
        return float(difflib.SequenceMatcher(None, s1, s2).ratio())
    FUZZY_ENGINE = "difflib (fallback)"

# -----------------------------------------------------------------------------
# Structured Logging Configuration (CLI Console + Persistent Log File)
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def setup_logging(log_file: Optional[str] = None) -> Path:
    """Configures dual logging to both console (CLI output) and persistent log file."""
    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = PROJECT_ROOT / log_path
    else:
        log_path = PROJECT_ROOT / "logs" / "deduplicate_and_load.log"

    log_path.parent.mkdir(parents=True, exist_ok=True)

    log_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger_instance = logging.getLogger("DedupPipeline")
    logger_instance.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if not logger_instance.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        logger_instance.addHandler(console_handler)

        file_handler = logging.FileHandler(str(log_path), mode="a", encoding="utf-8")
        file_handler.setFormatter(log_formatter)
        logger_instance.addHandler(file_handler)

    return log_path

logger = logging.getLogger("DedupPipeline")
setup_logging()


# Default Category Prefix Mapping
DEFAULT_PREFIXES: Dict[str, str] = {
    "fabric": "FAB",
    "trim": "TRM",
    "thread": "THD",
    "label": "LBL",
    "packaging": "PKG",
    "uncategorized": "UNC",
    "default": "GEN",
}

# -----------------------------------------------------------------------------
# Data Structures
# -----------------------------------------------------------------------------

class UnionFind:
    """Disjoint Set Union (DSU) with Path Compression and Union-by-Rank."""

    def __init__(self, elements: range | list):
        self.parent = {x: x for x in elements}
        self.rank = {x: 0 for x in elements}

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        # Path compression
        curr = x
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt
        return root

    def union(self, x: int, y: int) -> None:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

    def get_components(self) -> Dict[int, List[int]]:
        """Returns mapping of root_id -> list of element IDs belonging to that cluster."""
        components: Dict[int, List[int]] = {}
        for x in self.parent:
            root = self.find(x)
            components.setdefault(root, []).append(x)
        return components


# -----------------------------------------------------------------------------
# Normalization Functions
# -----------------------------------------------------------------------------

def normalize_material_name(text_val: Optional[str]) -> str:
    """
    Deterministic normalization:
    1. Lowercase
    2. Symbol replacement ('×' -> 'x', '&' -> 'and', '%' -> 'percent', etc.)
    3. Dimension separator between digits (e.g., 2x2 -> 2 2)
    4. Remove punctuation and non-alphanumeric characters
    5. Alphabetical sorting of word tokens (eliminating word-order variance)
    """
    if text_val is None or pd.isna(text_val):
        return ""

    cleaned = str(text_val).lower().strip()

    symbol_replacements = {
        "&": " and ",
        "%": " percent ",
        "+": " plus ",
        "@": " at ",
        "#": " number ",
        "/": " ",
        "-": " ",
        "_": " ",
        "×": " x ",
    }
    for sym, rep in symbol_replacements.items():
        cleaned = cleaned.replace(sym, rep)

    # Dimension separator only between digits (e.g. 2x2 -> 2 2)
    cleaned = re.sub(r"(?<=\d)x(?=\d)", " ", cleaned)

    # Remove remaining punctuation
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)

    # Token sort
    tokens = [tok for tok in cleaned.split() if tok]
    tokens.sort()

    return " ".join(tokens)


def normalize_category_slug(category_name: Optional[str]) -> str:
    """Normalizes category string into a key slug."""
    if not category_name or pd.isna(category_name):
        return "uncategorized"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(category_name).strip().lower()).strip("_")
    return slug or "uncategorized"


def get_category_prefix(category_name: str, prefix_map: Dict[str, str]) -> str:
    """Resolves standard 3-character prefix for master code generation."""
    slug = normalize_category_slug(category_name)
    if slug in prefix_map:
        return prefix_map[slug]
    for key, val in prefix_map.items():
        if key in slug or slug in key:
            return val
    return prefix_map.get("default", "GEN")


# -----------------------------------------------------------------------------
# Database Connection Helper
# -----------------------------------------------------------------------------

def get_db_engine(db_url: Optional[str] = None) -> Engine:
    """Creates a SQLAlchemy engine using provided URL or environment variables."""
    if not HAS_SQLALCHEMY:
        raise ImportError("SQLAlchemy is required. Install via: pip install sqlalchemy")

    load_dotenv()

    url = db_url or os.getenv("DATABASE_URL")
    if not url:
        user = os.getenv("DB_USER", "postgres")
        pwd = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db = os.getenv("DB_NAME", "postgres")
        url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

    logger.info("Connecting to database: %s", re.sub(r":([^:@]+)@", ":****@", url))
    return create_engine(url, pool_pre_ping=True)


# -----------------------------------------------------------------------------
# Step 1: Data Extraction
# -----------------------------------------------------------------------------

def extract_data(engine: Engine, table_name: str = "raw_materials") -> pd.DataFrame:
    """
    Extracts raw material records from the source table.
    Validates required columns and cleans category values.
    """
    logger.info("Step 1: Extracting raw data from table '%s'...", table_name)
    
    query = f"SELECT * FROM {table_name}"
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    if df.empty:
        raise ValueError(f"Source table '{table_name}' contains no records.")

    logger.info("Extracted %d records from '%s'.", len(df), table_name)

    # Normalize column names for flexible matching
    col_mapping: Dict[str, str] = {}
    for col in df.columns:
        norm_c = col.strip().lower().replace("/", "_").replace(" ", "_")
        if norm_c in ["material_item_code", "material_code", "item_code"]:
            col_mapping[col] = "material_item_code"
        elif norm_c in ["material_name", "item_name"]:
            col_mapping[col] = "material_name"
        elif norm_c == "category":
            col_mapping[col] = "category"
        else:
            col_mapping[col] = norm_c

    df = df.rename(columns=col_mapping)

    # Validate essential primary/clustering columns
    if "material_item_code" not in df.columns:
        raise KeyError("Required column 'material_item_code' (or 'Material/item code') not found.")
    if "material_name" not in df.columns:
        raise KeyError("Required column 'material_name' not found in source dataset.")

    # Convert essential columns to string
    df["material_item_code"] = df["material_item_code"].astype(str).str.strip()
    df["material_name"] = df["material_name"].astype(str).str.strip()

    # Clean category column: impute "Uncategorized" for missing or blank values
    if "category" not in df.columns:
        df["category"] = "Uncategorized"
    else:
        df["category"] = df["category"].fillna("Uncategorized").astype(str).str.strip()
        df["category"] = df["category"].replace({"": "Uncategorized", "nan": "Uncategorized", "None": "Uncategorized"})

    # Ensure uniqueness of child Primary Key: material_item_code
    # If the raw data contains duplicate legacy item codes across records, disambiguate them
    # while preserving traceability so that database PK constraints are not violated.
    if df["material_item_code"].duplicated().any():
        num_dupes = df["material_item_code"].duplicated().sum()
        logger.warning(
            "Detected %d duplicate 'material_item_code' entries in raw data. "
            "Disambiguating duplicate keys (appending #<idx>) to enforce PRIMARY KEY integrity.",
            num_dupes,
        )
        cum_count = df.groupby("material_item_code").cumcount()
        df["raw_item_code_original"] = df["material_item_code"]
        df["material_item_code"] = df.apply(
            lambda r: f"{r['material_item_code']}#{cum_count[r.name]}" if cum_count[r.name] > 0 else r["material_item_code"],
            axis=1,
        )

    return df


# -----------------------------------------------------------------------------
# Step 2: Deduplication & Clustering
# -----------------------------------------------------------------------------

def deduplicate_and_cluster(
    df: pd.DataFrame,
    similarity_threshold: float = 0.85,
    prefix_map: Optional[Dict[str, str]] = None,
    pad_length: int = 6,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Deduplicates strictly based on Material name within category partitions.
    Produces:
      - master_materials (Parent DataFrame)
      - material_records_mapped (Child DataFrame)
    """
    logger.info("Step 2: Clustering and deduplicating using %s (threshold=%.2f)...", FUZZY_ENGINE, similarity_threshold)
    prefixes = prefix_map or DEFAULT_PREFIXES

    # Deterministic normalization of Material name
    unique_raw_names = df["material_name"].unique()
    norm_cache = {raw: normalize_material_name(raw) for raw in unique_raw_names}
    df["norm_material_name"] = df["material_name"].map(norm_cache)

    master_records: List[Dict[str, Any]] = []
    mapped_records: List[pd.DataFrame] = []

    # Process each category independently
    for category_name, cat_df in df.groupby("category", sort=False):
        cat_df = cat_df.copy().reset_index(drop=True)
        prefix = get_category_prefix(category_name, prefixes)
        n_rows = len(cat_df)

        # Aggregate rows sharing identical normalized names to bypass quadratic overhead
        norm_to_rows: Dict[str, List[int]] = {}
        for idx, norm_nm in enumerate(cat_df["norm_material_name"]):
            norm_to_rows.setdefault(norm_nm, []).append(idx)

        unique_norm_names = list(norm_to_rows.keys())
        m = len(unique_norm_names)

        # Candidate pair generation
        candidate_pairs: Set[Tuple[int, int]] = set()
        if m <= 600:
            # Full pairwise comparison for small subsets
            for i in range(m):
                for j in range(i + 1, m):
                    candidate_pairs.add((i, j))
        else:
            # Token and prefix blocking for larger subsets
            token_index: Dict[str, List[int]] = {}
            for u_idx, name in enumerate(unique_norm_names):
                tokens = set(name.split())
                for tok in tokens:
                    if len(tok) >= 3:
                        token_index.setdefault(f"t_{tok}", []).append(u_idx)
                if len(name) >= 4:
                    token_index.setdefault(f"p_{name[:4]}", []).append(u_idx)

            max_block_size = 400
            for members in token_index.values():
                if 1 < len(members) <= max_block_size:
                    for i in range(len(members)):
                        for j in range(i + 1, len(members)):
                            a, b = members[i], members[j]
                            candidate_pairs.add((a, b) if a < b else (b, a))

        # Union-Find Clustering
        uf = UnionFind(range(m))
        for u1, u2 in candidate_pairs:
            s1, s2 = unique_norm_names[u1], unique_norm_names[u2]
            # Length filter heuristic: skip if length difference exceeds ratio
            max_len = max(len(s1), len(s2))
            if max_len > 0 and (min(len(s1), len(s2)) / max_len) < similarity_threshold:
                continue

            sim = compute_string_similarity(s1, s2)
            if sim >= similarity_threshold:
                uf.union(u1, u2)

        components = uf.get_components()

        # Build output arrays for this partition
        cluster_ids = [0] * n_rows
        scores = [1.0] * n_rows
        master_codes = [""] * n_rows
        cluster_counts = [1] * n_rows

        sorted_roots = sorted(components.keys(), key=lambda r: min(components[r]))
        for cluster_id, root in enumerate(sorted_roots, start=1):
            members = components[root]
            # All row indexes in this cluster
            cluster_row_indices = [r for u in members for r in norm_to_rows[unique_norm_names[u]]]
            record_count = len(cluster_row_indices)
            new_code = f"{prefix}-{str(cluster_id).zfill(pad_length)}"

            # Select canonical representative:
            # Most frequent raw name in cluster; ties broken by shortest length, then alphabetical
            raw_names_in_cluster = cat_df.loc[cluster_row_indices, "material_name"]
            counts = raw_names_in_cluster.value_counts()
            max_freq = counts.max()
            top_candidates = counts[counts == max_freq].index.tolist()
            canonical_name = min(top_candidates, key=lambda s: (len(s), s))
            canonical_norm = normalize_material_name(canonical_name)

            # Record parent master record
            master_records.append({
                "new_master_code": new_code,
                "canonical_material_name": canonical_name,
                "norm_material_name": canonical_norm,
                "category": category_name,
                "cluster_id": cluster_id,
                "cluster_record_count": record_count,
            })

            # Calculate individual similarity scores relative to canonical representative
            for u in members:
                norm_str = unique_norm_names[u]
                u_score = 1.0 if norm_str == canonical_norm else round(compute_string_similarity(norm_str, canonical_norm), 4)
                for r in norm_to_rows[norm_str]:
                    cluster_ids[r] = cluster_id
                    scores[r] = u_score
                    master_codes[r] = new_code
                    cluster_counts[r] = record_count

        cat_df["cluster_id"] = cluster_ids
        cat_df["new_master_code"] = master_codes
        cat_df["similarity_score"] = scores
        cat_df["cluster_record_count"] = cluster_counts
        cat_df["is_duplicate"] = cat_df["cluster_record_count"] > 1

        mapped_records.append(cat_df)

    df_master = pd.DataFrame(master_records)
    df_mapped = pd.concat(mapped_records, ignore_index=True)

    logger.info(
        "Clustering complete. Master items: %d, Mapped raw items: %d, Duplicates flagged: %d",
        len(df_master),
        len(df_mapped),
        int(df_mapped["is_duplicate"].sum()),
    )
    return df_master, df_mapped


# -----------------------------------------------------------------------------
# Step 3: Database Ingestion & Relational Integrity
# -----------------------------------------------------------------------------

def load_relational_tables(
    engine: Engine,
    df_master: pd.DataFrame,
    df_mapped: pd.DataFrame,
    chunksize: int = 5000,
) -> None:
    """
    Executes DDL to construct destination schema with foreign key constraints,
    and loads records in relational dependency order.
    """
    logger.info("Step 3: Ingesting normalized tables into database...")
    is_sqlite = engine.dialect.name == "sqlite"

    # Identify extra raw spec columns to retain in material_records_mapped
    standard_cols = {
        "material_item_code", "new_master_code", "material_name",
        "category", "is_duplicate", "similarity_score", "cluster_id",
        "cluster_record_count", "norm_material_name", "raw_item_code_original",
    }
    raw_spec_cols = [c for c in df_mapped.columns if c not in standard_cols]

    # Clean spec columns: sanitize names for SQL
    sql_spec_definitions = []
    clean_mapped_cols = {}
    for c in raw_spec_cols:
        clean_c = re.sub(r"[^\w]", "_", c).strip("_")
        clean_mapped_cols[c] = clean_c
        sql_spec_definitions.append(f"{clean_c} TEXT")

    df_mapped = df_mapped.rename(columns=clean_mapped_cols)

    spec_ddl_fragment = ", " + ", ".join(sql_spec_definitions) if sql_spec_definitions else ""

    # DDL Statements
    ddl_drop_child = "DROP TABLE IF EXISTS material_records_mapped CASCADE;" if not is_sqlite else "DROP TABLE IF EXISTS material_records_mapped;"
    ddl_drop_parent = "DROP TABLE IF EXISTS master_materials CASCADE;" if not is_sqlite else "DROP TABLE IF EXISTS master_materials;"

    ddl_create_parent = """
    CREATE TABLE master_materials (
        new_master_code         VARCHAR(50) PRIMARY KEY,
        canonical_material_name TEXT NOT NULL,
        norm_material_name      TEXT NOT NULL,
        category                VARCHAR(100) NOT NULL,
        cluster_id              INTEGER NOT NULL,
        cluster_record_count    INTEGER NOT NULL
    );
    """

    ddl_create_child = f"""
    CREATE TABLE material_records_mapped (
        material_item_code      VARCHAR(100) PRIMARY KEY,
        new_master_code         VARCHAR(50) NOT NULL REFERENCES master_materials(new_master_code) ON DELETE CASCADE,
        material_name           TEXT NOT NULL,
        category                VARCHAR(100) NOT NULL,
        is_duplicate            BOOLEAN NOT NULL,
        similarity_score        FLOAT NOT NULL,
        cluster_id              INTEGER NOT NULL,
        cluster_record_count    INTEGER NOT NULL
        {spec_ddl_fragment}
    );
    """

    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(text("PRAGMA foreign_keys = OFF;"))

        logger.info("Executing DDL drop and create statements...")
        conn.execute(text(ddl_drop_child))
        conn.execute(text(ddl_drop_parent))
        conn.execute(text(ddl_create_parent))
        conn.execute(text(ddl_create_child))

        if is_sqlite:
            conn.execute(text("PRAGMA foreign_keys = ON;"))

    # Prepare Parent Table Data
    master_cols_to_load = [
        "new_master_code", "canonical_material_name", "norm_material_name",
        "category", "cluster_id", "cluster_record_count",
    ]
    df_master_clean = df_master[master_cols_to_load].copy()

    # Prepare Child Table Data
    mapped_base_cols = [
        "material_item_code", "new_master_code", "material_name",
        "category", "is_duplicate", "similarity_score",
        "cluster_id", "cluster_record_count",
    ]
    mapped_cols_to_load = mapped_base_cols + [clean_mapped_cols[c] for c in raw_spec_cols]
    df_mapped_clean = df_mapped[mapped_cols_to_load].copy()

    # Ingest Parent Table First (Strict Relational Order)
    logger.info("Inserting %d rows into parent table 'master_materials'...", len(df_master_clean))
    df_master_clean.to_sql(
        name="master_materials",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
        method="multi" if is_sqlite else None,
    )

    # Ingest Child Table Second
    logger.info("Inserting %d rows into child table 'material_records_mapped'...", len(df_mapped_clean))
    df_mapped_clean.to_sql(
        name="material_records_mapped",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
        method="multi" if is_sqlite else None,
    )

    # Validate Foreign Key Relational Integrity
    logger.info("Validating Foreign Key relational constraints...")
    validation_query = """
    SELECT COUNT(*) AS orphan_count
    FROM material_records_mapped c
    LEFT JOIN master_materials p ON c.new_master_code = p.new_master_code
    WHERE p.new_master_code IS NULL;
    """
    with engine.connect() as conn:
        res = conn.execute(text(validation_query)).scalar()
        if res and res > 0:
            raise ValueError(f"Relational integrity violation: Found {res} orphaned records in child table!")
        logger.info("Foreign key integrity verification PASSED (0 orphan records).")


# -----------------------------------------------------------------------------
# Optional Seeding Utility (For Local/Test Runs)
# -----------------------------------------------------------------------------

def seed_raw_table_if_needed(engine: Engine, csv_path: str, table_name: str = "raw_materials") -> None:
    """Seeds the source table from a CSV file if the table does not exist or is empty."""
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as conn:
        # Check if table exists
        check_q = (
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';"
            if is_sqlite
            else f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}';"
        )
        table_exists = conn.execute(text(check_q)).scalar() is not None

        if table_exists:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name};")).scalar()
            if count and count > 0:
                logger.info("Table '%s' already contains %d records. Skipping seeding.", table_name, count)
                return

    logger.info("Seeding '%s' from CSV: %s ...", table_name, csv_path)
    df_csv = pd.read_csv(csv_path, dtype=str)
    # Standardize column headers
    df_csv.columns = [re.sub(r"[^\w]", "_", c).strip("_").lower() for c in df_csv.columns]
    df_csv.to_sql(name=table_name, con=engine, if_exists="replace", index=False, chunksize=10000)
    logger.info("Seeding complete (%d rows imported).", len(df_csv))


# -----------------------------------------------------------------------------
# Main Execution Pipeline
# -----------------------------------------------------------------------------

def run_pipeline(
    db_url: Optional[str] = None,
    csv_seed_path: Optional[str] = None,
    similarity_threshold: float = 0.85,
    source_table: str = "raw_materials",
    log_file: Optional[str] = None,
) -> None:
    """Executes the complete End-to-End Material Deduplication & Ingestion Pipeline."""
    log_path = setup_logging(log_file)
    start_time = time.time()
    start_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info("=" * 80)
    logger.info(">>> STARTING DEDUPLICATION & RELATIONAL PIPELINE RUN <<<")
    logger.info("Program Run Started At: %s", start_dt)
    logger.info("Persistent Log File   : %s", log_path)
    logger.info("=" * 80)

    engine = get_db_engine(db_url)

    # Optional seeding if requested
    if csv_seed_path:
        seed_raw_table_if_needed(engine, csv_seed_path, source_table)

    # Step 1: Extract
    df_raw = extract_data(engine, source_table)

    # Step 2: Deduplicate & Cluster
    df_master, df_mapped = deduplicate_and_cluster(df_raw, similarity_threshold=similarity_threshold)

    # Step 3: Ingest Normalized Tables
    load_relational_tables(engine, df_master, df_mapped)

    elapsed = time.time() - start_time
    end_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_raw = len(df_mapped)
    unique_masters = len(df_master)
    duplicate_rows = int(df_mapped["is_duplicate"].sum())
    reduction_pct = ((total_raw - unique_masters) / total_raw * 100) if total_raw else 0.0

    logger.info("=" * 80)
    logger.info(">>> PIPELINE EXECUTION FINISHED SUCCESSFULLY IN %.2f SECONDS <<<", elapsed)
    logger.info("Program Run Started At: %s", start_dt)
    logger.info("Program Run Finished At: %s", end_dt)
    logger.info("Pipeline Summary Metrics:")
    logger.info("  - Total Raw Records Processed: %d", total_raw)
    logger.info("  - Unique Master Items Created: %d", unique_masters)
    logger.info("  - Records Flagged as Duplicate: %d", duplicate_rows)
    logger.info("  - SKU / Catalog Redundancy Reduction: %.2f%%", reduction_pct)
    logger.info("=" * 80 + "\n")


# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end Material Deduplication & Normalization SQL Pipeline.")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL (Postgres or SQLite).")
    parser.add_argument("--seed-csv", type=str, default=None, help="Optional CSV file path to seed raw_materials table.")
    parser.add_argument("--threshold", type=float, default=0.85, help="Fuzzy string similarity threshold (default: 0.85).")
    parser.add_argument("--source-table", type=str, default="raw_materials", help="Source table name (default: raw_materials).")
    parser.add_argument("--log-file", type=str, default=None, help="Custom log file path (default: logs/deduplicate_and_load.log).")

    args = parser.parse_args()

    try:
        run_pipeline(
            db_url=args.db_url,
            csv_seed_path=args.seed_csv,
            similarity_threshold=args.threshold,
            source_table=args.source_table,
            log_file=args.log_file,
        )
    except Exception as e:
        logger.exception("Pipeline failed: %s", str(e))
        sys.exit(1)

