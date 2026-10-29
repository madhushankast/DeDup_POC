import os
import re
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment credentials from .env
load_dotenv()

# Page configuration & Modern Styling
st.set_page_config(
    page_title="Material Master & Deduplication Dashboard",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Modern Theme-Adaptive Styling (Dark & Light Mode Compatible)
st.markdown(
    """
    <style>
    /* Hide Empty Sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Uniform-Height, Theme-Adaptive KPI Cards */
    .kpi-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 14px;
        padding: 18px 20px;
        height: 142px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        backdrop-filter: blur(10px);
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
        box-sizing: border-box;
        margin-bottom: 8px;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        border-color: #3b82f6;
        box-shadow: 0 10px 24px -4px rgba(59, 130, 246, 0.25);
    }
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 600;
        opacity: 0.82;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    .kpi-icon {
        font-size: 1.25rem;
        opacity: 0.9;
    }
    .kpi-value {
        font-size: 2.15rem;
        font-weight: 700;
        line-height: 1.1;
        letter-spacing: -0.5px;
        margin: 4px 0;
    }
    .kpi-footer {
        display: flex;
        align-items: center;
        min-height: 24px;
    }
    .kpi-badge {
        font-size: 0.78rem;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-green {
        background: rgba(34, 197, 94, 0.16);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.32);
    }
    .badge-blue {
        background: rgba(59, 130, 246, 0.16);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.32);
    }
    .badge-purple {
        background: rgba(168, 85, 247, 0.16);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.32);
    }
    .badge-neutral {
        background: rgba(148, 163, 184, 0.14);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.22);
    }

    /* Top Header & Navigation Banner */
    .top-header-banner {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.45) 0%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 14px;
        padding: 18px 24px;
        margin-bottom: 14px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        backdrop-filter: blur(12px);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 14px;
    }
    .top-header-left {
        display: flex;
        flex-direction: column;
    }
    .top-header-title {
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
        letter-spacing: -0.3px;
    }
    .top-header-caption {
        font-size: 0.9rem;
        opacity: 0.76;
        margin-top: 5px;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        padding: 7px 16px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.2px;
    }
    .status-pill-green {
        background: rgba(34, 197, 94, 0.14);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.35);
        box-shadow: 0 0 14px rgba(34, 197, 94, 0.15);
    }
    .status-pill-blue {
        background: rgba(59, 130, 246, 0.14);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.35);
        box-shadow: 0 0 14px rgba(59, 130, 246, 0.15);
    }
    .status-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-green {
        background-color: #22c55e;
        box-shadow: 0 0 8px #22c55e;
        animation: status-pulse-green 2s infinite ease-in-out;
    }
    .dot-blue {
        background-color: #3b82f6;
        box-shadow: 0 0 8px #3b82f6;
        animation: status-pulse-blue 2s infinite ease-in-out;
    }
    @keyframes status-pulse-green {
        0% { transform: scale(0.9); opacity: 0.8; box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.6); }
        70% { transform: scale(1.15); opacity: 1; box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
        100% { transform: scale(0.9); opacity: 0.8; box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }
    @keyframes status-pulse-blue {
        0% { transform: scale(0.9); opacity: 0.8; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.6); }
        70% { transform: scale(1.15); opacity: 1; box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); }
        100% { transform: scale(0.9); opacity: 0.8; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }

    /* Top Navigation Switcher Row */
    .top-nav-container {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 12px;
        padding: 8px 14px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .nav-label {
        font-weight: 700;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        opacity: 0.78;
        padding-right: 6px;
    }

    /* Modern horizontal radio button styling */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        gap: 10px;
        background: rgba(255, 255, 255, 0.03);
        padding: 4px 6px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.16);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 6px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        font-size: 0.92rem;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background: rgba(59, 130, 246, 0.1);
        border-color: rgba(59, 130, 246, 0.3);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
        background: rgba(59, 130, 246, 0.2);
        border-color: #3b82f6;
        color: #60a5fa;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.22);
    }

    /* Styled Metric Cards for Global Pipeline Summary Banner */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 12px;
        padding: 14px 18px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #3b82f6;
        box-shadow: 0 8px 20px -4px rgba(59, 130, 246, 0.2);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.35px !important;
        opacity: 0.82 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_kpi_card(title: str, value: str, badge_text: str = "", badge_type: str = "neutral", icon: str = ""):
    """Renders a pixel-perfect, uniform-height KPI card matching modern dark/light UI/UX design."""
    badge_html = f'<span class="kpi-badge badge-{badge_type}">{badge_text}</span>' if badge_text else ''
    icon_html = f'<span class="kpi-icon">{icon}</span>' if icon else ''
    card_html = f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <span class="kpi-title">{title}</span>
            {icon_html}
        </div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-footer">
            {badge_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def apply_chart_theme(fig):
    """Ensures Plotly charts seamlessly adapt to dark or light themes with transparent canvas."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=45, l=15, r=15, b=25),
    )
    return fig




@st.cache_resource
def get_database_engine():
    """Builds a cached SQLAlchemy database engine using Streamlit Secrets or .env DATABASE_URL (Supabase)."""
    url = None
    # 1. Check Streamlit Secrets (used in Streamlit Community Cloud)
    try:
        if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
            url = st.secrets["DATABASE_URL"]
    except Exception:
        pass

    # 2. Check Environment Variables / .env
    if not url:
        url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError(
            "DATABASE_URL is not configured. Please set DATABASE_URL with your Supabase connection string in .env or Streamlit Secrets."
        )

    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=600)
def load_data():
    """
    Loads datasets from PostgreSQL with automatic fallback to repository data.
    Ensures seamless deployment on Streamlit Community Cloud even without a public DB instance.
    """
    data_source_mode = "PostgreSQL Database"
    try:
        engine = get_database_engine()

        # Load raw materials
        with engine.connect() as conn:
            df_raw = pd.read_sql("SELECT * FROM raw_materials", conn)

        # Check if normalized deduplication tables exist
        has_dedup = False
        df_master = pd.DataFrame()
        df_mapped = pd.DataFrame()

        with engine.connect() as conn:
            check_q = text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('master_materials', 'material_records_mapped');"
            )
            existing_tables = [row[0] for row in conn.execute(check_q).fetchall()]

        if "master_materials" in existing_tables and "material_records_mapped" in existing_tables:
            with engine.connect() as conn:
                df_master = pd.read_sql("SELECT * FROM master_materials", conn)
                df_mapped = pd.read_sql(
                    "SELECT material_item_code, new_master_code, material_name, category, is_duplicate, similarity_score, cluster_id, cluster_record_count FROM material_records_mapped",
                    conn,
                )
            has_dedup = True

        return df_raw, df_master, df_mapped, has_dedup, data_source_mode

    except Exception as db_err:
        # Fallback to local repository CSV files (Streamlit Community Cloud Mode)
        root_dir = Path(__file__).resolve().parent
        raw_csv = root_dir / "data" / "01_raw" / "raw_materials.csv"
        unique_dir = root_dir / "data" / "05_unique"
        curated_dir = root_dir / "data" / "04_curated"

        if raw_csv.exists():
            df_raw = pd.read_csv(raw_csv, dtype=str)
            col_map = {c: c.strip().lower().replace("/", "_").replace(" ", "_") for c in df_raw.columns}
            df_raw = df_raw.rename(columns=col_map)
            if "category" in df_raw.columns:
                df_raw["category"] = df_raw["category"].fillna("Uncategorized").replace({"": "Uncategorized"})

            master_files = sorted(unique_dir.glob("unique_master_*.csv")) if unique_dir.exists() else []
            curated_files = sorted(curated_dir.glob("curated_*.csv")) if curated_dir.exists() else []

            df_master = pd.concat([pd.read_csv(f, dtype=str) for f in master_files], ignore_index=True) if master_files else pd.DataFrame()
            df_mapped = pd.concat([pd.read_csv(f, dtype=str) for f in curated_files], ignore_index=True) if curated_files else pd.DataFrame()

            if not df_master.empty and "Material name" in df_master.columns:
                df_master = df_master.rename(columns={"Material name": "canonical_material_name"})
            if not df_mapped.empty:
                col_map_mapped = {c: c.strip().lower().replace("/", "_").replace(" ", "_") for c in df_mapped.columns}
                df_mapped = df_mapped.rename(columns=col_map_mapped)
                if "is_duplicate" in df_mapped.columns:
                    df_mapped["is_duplicate"] = df_mapped["is_duplicate"].astype(str).str.lower().isin(["true", "1"])
                if "similarity_score" in df_mapped.columns:
                    df_mapped["similarity_score"] = pd.to_numeric(df_mapped["similarity_score"], errors="coerce").fillna(1.0)

            has_dedup = not df_master.empty and not df_mapped.empty
            data_source_mode = "Repository Data (Streamlit Cloud Demo)"
            return df_raw, df_master, df_mapped, has_dedup, data_source_mode
        else:
            raise db_err


try:
    df_raw, df_master, df_mapped, has_dedup, data_source_mode = load_data()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.info("Please verify your database credentials in `.env` or verify the repository data directory.")
    st.stop()

# =============================================================================
# NAVIGATION CONFIGURATION
# =============================================================================
PAGE_OPTIONS = (
    [
        "📊 Raw Materials Overview",
        "🏛️ Master Catalog Explorer",
        "🔗 Raw Item Tracking with Foreign Key",
    ]
    if has_dedup
    else ["📊 Raw Materials Overview"]
)

# Top Horizontal Header Navigation Bar
nav_col_left, nav_col_center, nav_col_right = st.columns([1.5, 4.5, 1.2], vertical_alignment="center")

with nav_col_left:
    status_color = "#22c55e" if "PostgreSQL" in data_source_mode else "#60a5fa"
    status_bg = "rgba(34, 197, 94, 0.14)" if "PostgreSQL" in data_source_mode else "rgba(59, 130, 246, 0.14)"
    status_border = "rgba(34, 197, 94, 0.35)" if "PostgreSQL" in data_source_mode else "rgba(59, 130, 246, 0.35)"
    icon_dot = "🟢" if "PostgreSQL" in data_source_mode else "☁️"
    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; background: {status_bg}; border: 1px solid {status_border}; border-radius: 20px; font-weight: 600; font-size: 0.88rem; color: {status_color}; white-space: nowrap;">
            <span>{icon_dot}</span>
            <span>{data_source_mode}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav_col_center:
    active_tab = st.segmented_control(
        "Select View",
        options=PAGE_OPTIONS,
        default=PAGE_OPTIONS[0],
        label_visibility="collapsed",
        key="top_nav_segmented",
    )
    if not active_tab:
        active_tab = PAGE_OPTIONS[0]

with nav_col_right:
    if st.button("🔄 Clear & Reload Cache", use_container_width=True, key="top_clear_cache_btn"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")


# =============================================================================
# PAGE 1: 📊 Raw Materials Overview
# =============================================================================
if active_tab == "📊 Raw Materials Overview":
    st.title("📊 Raw Materials Overview")
    st.caption("Uncleaned source inventory records from `raw_materials` prior to deduplication.")
    st.markdown("---")

    # Clean category column for dashboard display
    df_raw["category"] = df_raw["category"].fillna("Uncategorized").replace({"": "Uncategorized"})

    # Category volume distribution bar chart
    st.subheader("Category Volume Distribution")
    col_chart_left, col_chart_right = st.columns(2)

    with col_chart_left:
        cat_counts = df_raw["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Record Count"]
        cat_fig = px.bar(
            cat_counts,
            x="Category",
            y="Record Count",
            title="Raw Materials Volume per Category",
            text="Record Count",
            color="Category",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        cat_fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        cat_fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Number of Items")
        st.plotly_chart(apply_chart_theme(cat_fig), use_container_width=True)

    with col_chart_right:
        if "inventory_uom" in df_raw.columns:
            uom_fig = px.pie(
                df_raw,
                names="inventory_uom",
                title="Distribution by Inventory Unit of Measure (UOM)",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            uom_fig.update_traces(textinfo="percent+label")
            st.plotly_chart(apply_chart_theme(uom_fig), use_container_width=True)

    st.markdown("---")

    # Filterable Data Table: raw_materials table with category filter dropdown and material name search box
    st.subheader("Raw Materials Table Explorer (`raw_materials`)")

    col_filter1, col_filter2 = st.columns([1, 2])
    with col_filter1:
        cat_options = ["All"] + sorted([str(c) for c in df_raw["category"].unique()])
        selected_category = st.selectbox("Filter by Category", cat_options)

    with col_filter2:
        search_query = st.text_input("🔍 Search by Material Name or Code", "", key="raw_search_query")

    # Apply filters
    filtered_df = df_raw
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df["category"] == selected_category]

    if search_query.strip():
        q = search_query.strip().lower()
        name_col = next((c for c in filtered_df.columns if "name" in c.lower()), "material_name")
        code_col = next((c for c in filtered_df.columns if "code" in c.lower()), "material_code")
        filtered_df = filtered_df[
            filtered_df[name_col].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df[code_col].astype(str).str.lower().str.contains(q, na=False)
        ]

    st.caption(f"Displaying **{len(filtered_df):,}** matching raw inventory records (showing up to 500 in grid):")
    st.dataframe(filtered_df.head(500), use_container_width=True)

    # CSV Download Option
    csv_bytes = filtered_df.head(1000).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Raw Records as CSV",
        data=csv_bytes,
        file_name=f"raw_materials_{selected_category.lower()}.csv",
        mime="text/csv",
        key="raw_download_btn",
    )


# =============================================================================
# PAGE 2: 🏛️ Master Catalog Explorer (master_materials)
# =============================================================================
elif (active_tab == "🏛️ Master Catalog Explorer" or "Master Catalog Explorer" in active_tab) and has_dedup:
    st.title("🏛️ Master Catalog Explorer")
    st.caption("Canonical master catalog with one consolidated entity per unique material (`new_master_code`).")
    st.markdown("---")

    # Convert numeric fields for accurate aggregation
    if "cluster_record_count" in df_master.columns:
        df_master["cluster_record_count"] = pd.to_numeric(df_master["cluster_record_count"], errors="coerce").fillna(1).astype(int)

    # Ensure required parent columns exist
    if "norm_material_name" not in df_master.columns and "canonical_material_name" in df_master.columns:
        df_master["norm_material_name"] = df_master["canonical_material_name"].astype(str).str.lower().str.strip()

    # Top-Cluster Bar Chart & Category Distribution
    col_master_chart1, col_master_chart2 = st.columns(2)

    with col_master_chart1:
        st.markdown("##### Top 10 Canonical Materials by Record Count")
        top_clusters = df_master.sort_values(by="cluster_record_count", ascending=False).head(10)
        fig_top_clusters = px.bar(
            top_clusters,
            x="cluster_record_count",
            y="canonical_material_name",
            orientation="h",
            title="Highest Variation Duplicate Clusters",
            labels={"cluster_record_count": "Raw Variations in Cluster", "canonical_material_name": "Canonical Material Name"},
            color="cluster_record_count",
            color_continuous_scale="Reds",
        )
        fig_top_clusters.update_layout(yaxis={"autorange": "reversed"})
        st.plotly_chart(apply_chart_theme(fig_top_clusters), use_container_width=True)

    with col_master_chart2:
        st.markdown("##### Canonical Master Items by Category")
        master_cat = df_master["category"].value_counts().reset_index()
        master_cat.columns = ["Category", "Unique Master Items"]
        fig_master_cat = px.bar(
            master_cat,
            x="Category",
            y="Unique Master Items",
            title="Standard Master Items by Category",
            text="Unique Master Items",
            color="Category",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_master_cat.update_traces(texttemplate="%{text:,}", textposition="outside")
        st.plotly_chart(apply_chart_theme(fig_master_cat), use_container_width=True)

    st.markdown("---")

    # Display Parent Table: master_materials
    st.subheader("Parent Entity Table (`master_materials`)")

    # Required columns: new_master_code, canonical_material_name, norm_material_name, category, cluster_id, cluster_record_count
    target_master_cols = [
        "new_master_code",
        "canonical_material_name",
        "norm_material_name",
        "category",
        "cluster_id",
        "cluster_record_count",
    ]
    available_cols = [c for c in target_master_cols if c in df_master.columns]
    remaining_cols = [c for c in df_master.columns if c not in available_cols]
    ordered_master_df = df_master[available_cols + remaining_cols]

    col_m_search, col_m_cat = st.columns([2, 1])
    with col_m_search:
        m_search = st.text_input("🔍 Search Master Materials (by Code or Name)", "", key="master_search_input")
    with col_m_cat:
        m_categories = ["All"] + sorted([str(c) for c in ordered_master_df["category"].dropna().unique()])
        m_cat_select = st.selectbox("Filter Category", m_categories, key="master_cat_select")

    filtered_master = ordered_master_df
    if m_cat_select != "All":
        filtered_master = filtered_master[filtered_master["category"] == m_cat_select]
    if m_search.strip():
        mq = m_search.strip().lower()
        filtered_master = filtered_master[
            filtered_master["new_master_code"].astype(str).str.lower().str.contains(mq, na=False)
            | filtered_master["canonical_material_name"].astype(str).str.lower().str.contains(mq, na=False)
        ]

    st.caption(f"Displaying **{len(filtered_master):,}** canonical master materials (Primary Key: `new_master_code`):")
    st.dataframe(filtered_master, use_container_width=True)

    csv_master_bytes = filtered_master.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Master Catalog as CSV",
        data=csv_master_bytes,
        file_name="master_materials_catalog.csv",
        mime="text/csv",
        key="master_download_btn",
    )


# =============================================================================
# PAGE 3: 🔗 Raw Item Tracking with Foreign Key
# =============================================================================
elif active_tab == "🔗 Raw Item Tracking with Foreign Key" and has_dedup:
    st.title("🔗 Raw Item Tracking with Foreign Key")
    st.caption("Historical raw records mapped to their parent master code via foreign key relationship.")
    st.markdown("---")

    # Referential integrity validation check
    valid_masters = set(df_master["new_master_code"])
    orphan_mask = ~df_mapped["new_master_code"].isin(valid_masters)
    orphan_count = int(orphan_mask.sum())

    if orphan_count == 0:
        st.success("🛡️ **Relational Foreign Key Integrity:** Validated (0 Orphan Records) — All child rows strictly map to an existing `master_materials.new_master_code`.")
    else:
        st.error(f"⚠️ **Foreign Key Constraint Violation:** {orphan_count} orphan records detected without a corresponding parent master code.")

    # Master Code Drill-Down Section
    st.subheader("Master Code Variant Drill-Down")
    st.caption("Select any parent `new_master_code` to audit all raw legacy records mapped to it.")

    master_code_list = sorted(df_master["new_master_code"].tolist())
    name_lookup = dict(zip(df_master["new_master_code"], df_master["canonical_material_name"]))

    selected_master = st.selectbox(
        "Select / Search Master Code:",
        options=master_code_list,
        format_func=lambda code: f"{code} — {name_lookup.get(code, 'Unknown')}",
        key="master_drilldown_selector",
    )

    if selected_master:
        cluster_variants = df_mapped[df_mapped["new_master_code"] == selected_master]
        target_drill_cols = ["material_item_code", "material_name", "similarity_score", "is_duplicate"]
        available_drill_cols = [c for c in target_drill_cols if c in cluster_variants.columns]
        extra_drill_cols = [c for c in ["category", "cluster_id", "cluster_record_count"] if c in cluster_variants.columns]

        st.markdown(
            f"**Parent Code:** `{selected_master}` | **Canonical Material:** `{name_lookup.get(selected_master, '')}` | **Mapped Raw Variants:** `{len(cluster_variants)}`"
        )
        st.dataframe(cluster_variants[available_drill_cols + extra_drill_cols], use_container_width=True)

    st.markdown("---")

    # Full Mapped Child Table with is_duplicate filter toggles
    st.subheader("Child Tracking Entity Explorer (`material_records_mapped`)")

    col_child_filter1, col_child_filter2 = st.columns([2, 1])
    with col_child_filter1:
        dup_filter_option = st.radio(
            "Filter by Duplicate Status (`is_duplicate`):",
            options=["All Records", "Duplicates Only (True)", "Canonical Roots Only (False)"],
            horizontal=True,
            key="dup_filter_radio",
        )

    with col_child_filter2:
        child_search = st.text_input("🔍 Search Child Table (Code, Name, or Master)", "", key="child_search_input")

    # Filter by duplicate status toggle
    filtered_mapped = df_mapped
    if dup_filter_option == "Duplicates Only (True)":
        filtered_mapped = filtered_mapped[filtered_mapped["is_duplicate"] == True]
    elif dup_filter_option == "Canonical Roots Only (False)":
        filtered_mapped = filtered_mapped[filtered_mapped["is_duplicate"] == False]

    # Filter by search string
    if child_search.strip():
        cq = child_search.strip().lower()
        filtered_mapped = filtered_mapped[
            filtered_mapped["material_item_code"].astype(str).str.lower().str.contains(cq, na=False)
            | filtered_mapped["material_name"].astype(str).str.lower().str.contains(cq, na=False)
            | filtered_mapped["new_master_code"].astype(str).str.lower().str.contains(cq, na=False)
        ]

    st.caption(f"Displaying **{len(filtered_mapped):,}** mapped child items (showing up to 500 in grid):")
    st.dataframe(filtered_mapped.head(500), use_container_width=True)

    csv_child_bytes = filtered_mapped.head(2000).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Child Mapping Table as CSV",
        data=csv_child_bytes,
        file_name="material_records_mapped.csv",
        mime="text/csv",
        key="child_download_btn",
    )
