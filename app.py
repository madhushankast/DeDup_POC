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
    initial_sidebar_state="expanded",
)

# Modern Theme-Adaptive Styling (Dark & Light Mode Compatible)
st.markdown(
    """
    <style>
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

    /* Hero View Switcher Component */
    .view-switcher-title {
        font-size: 0.95rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        opacity: 0.85;
        margin: 10px 0 12px 2px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .view-card {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 14px;
        padding: 18px 20px;
        min-height: 156px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
        transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
        margin-bottom: 6px;
        box-sizing: border-box;
    }
    .view-card:hover {
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.55);
        box-shadow: 0 8px 24px -4px rgba(59, 130, 246, 0.22);
    }
    .view-card.active-card {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(139, 92, 246, 0.09));
        border: 2px solid #3b82f6;
        box-shadow: 0 10px 30px -4px rgba(59, 130, 246, 0.35);
    }
    .view-card.active-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
    }
    .view-card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 6px;
    }
    .view-card-headline {
        font-size: 1.15rem;
        font-weight: 700;
        line-height: 1.25;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .view-card-subtitle {
        font-size: 0.86rem;
        opacity: 0.8;
        line-height: 1.4;
        margin-bottom: 10px;
    }
    .view-card-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: auto;
        padding-top: 10px;
        border-top: 1px solid rgba(128, 128, 128, 0.15);
    }
    .view-card-stat {
        font-size: 0.84rem;
        font-weight: 600;
        opacity: 0.95;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .badge-star-feature {
        background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
        color: #ffffff !important;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        padding: 3px 10px;
        border-radius: 9999px;
        box-shadow: 0 2px 12px rgba(236, 72, 153, 0.45);
        display: inline-flex;
        align-items: center;
        gap: 5px;
        animation: pulse-glow 2.5s infinite ease-in-out;
    }
    .badge-baseline {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.32);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        padding: 3px 9px;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .status-indicator {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        padding: 2px 9px;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .status-indicator.active {
        background: rgba(34, 197, 94, 0.18);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.35);
    }
    .status-indicator.inactive {
        background: rgba(148, 163, 184, 0.12);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 8px rgba(236, 72, 153, 0.35); }
        50% { box-shadow: 0 0 20px rgba(236, 72, 153, 0.75); }
    }

    /* Enhanced Sidebar Navigation */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 10px;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 12px;
        padding: 12px 14px;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        cursor: pointer;
        display: flex;
        align-items: center;
        font-weight: 500;
        width: 100%;
        box-sizing: border-box;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(59, 130, 246, 0.08);
        border-color: #3b82f6;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(139, 92, 246, 0.18)) !important;
        border: 1.5px solid #3b82f6 !important;
        box-shadow: 0 4px 14px -2px rgba(59, 130, 246, 0.3);
        font-weight: 700;
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
    """Builds a cached SQLAlchemy database engine using Streamlit Secrets or .env credentials."""
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
        user = os.getenv("DB_USER", "postgres")
        pwd = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db = os.getenv("DB_NAME", "postgres")
        url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
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


# Header section
st.title("🧵 Apparel Raw Materials & Deduplication Dashboard")
st.caption("PostgreSQL Analytics, Catalog Normalization & Duplicate Management")

try:
    df_raw, df_master, df_mapped, has_dedup, data_source_mode = load_data()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.info("Please verify your database credentials in `.env` or verify the repository data directory.")
    st.stop()

# Pre-calculate high-level metrics for the hero cards and navigation
total_raw_count = len(df_raw)
total_master_count = len(df_master) if not df_master.empty else 0
dupes_count = int(df_mapped["is_duplicate"].sum()) if (not df_mapped.empty and "is_duplicate" in df_mapped.columns) else 0
reduction_rate = (((len(df_mapped) - total_master_count) / len(df_mapped)) * 100) if (not df_mapped.empty and len(df_mapped) > 0) else 0.0

VIEW_RAW = "📊 Raw Materials Overview"
VIEW_DEDUP = "✨ Master Deduplication & Clusters"
VIEW_OPTIONS = [VIEW_RAW, VIEW_DEDUP] if has_dedup else [VIEW_RAW]

# Initialize or synchronize session state (Default to Core Feature if available)
if "active_view" not in st.session_state or st.session_state["active_view"] not in VIEW_OPTIONS:
    st.session_state["active_view"] = VIEW_DEDUP if has_dedup else VIEW_RAW

# Sidebar Controls
st.sidebar.header("🧭 Navigation & Status")
if "PostgreSQL" in data_source_mode:
    st.sidebar.success(f"🟢 {data_source_mode}")
else:
    st.sidebar.info(f"☁️ {data_source_mode}")

def sync_sidebar():
    st.session_state["active_view"] = st.session_state["sidebar_radio_key"]

st.sidebar.markdown("**Select Active View:**")
active_sidebar = st.sidebar.radio(
    "Select View Mode",
    options=VIEW_OPTIONS,
    index=VIEW_OPTIONS.index(st.session_state["active_view"]),
    key="sidebar_radio_key",
    on_change=sync_sidebar,
    label_visibility="collapsed",
)
st.session_state["active_view"] = active_sidebar

if st.sidebar.button("🔄 Refresh Data Cache", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"""
    <div style="font-size: 0.8rem; opacity: 0.82; line-height: 1.45; padding: 4px 2px;">
        💡 <b>Core POC Feature</b>:<br>
        The <i>Master Deduplication & Clusters</i> module showcases <b>{reduction_rate:.1f}% SKU redundancy reduction</b> using AI cluster normalization.
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# HIGH-IMPACT HERO VIEW SWITCHER (MAIN CONTAINER)
# -----------------------------------------------------------------------------
st.markdown('<div class="view-switcher-title"><span>🎯 Select Dashboard View</span></div>', unsafe_allow_html=True)

nav_col1, nav_col2 = st.columns(2)

is_raw_active = st.session_state["active_view"] == VIEW_RAW
is_dedup_active = st.session_state["active_view"] == VIEW_DEDUP

with nav_col1:
    raw_status_class = "active" if is_raw_active else "inactive"
    raw_status_label = "● ACTIVE MODULE" if is_raw_active else "○ SWITCH TO VIEW"
    raw_card_class = "view-card active-card" if is_raw_active else "view-card"

    st.markdown(
        f"""
        <div class="{raw_card_class}">
            <div class="view-card-top">
                <div class="view-card-headline">
                    <span>📊</span>
                    <span>Raw Materials Overview</span>
                </div>
                <span class="badge-baseline">INGESTION BASELINE</span>
            </div>
            <div class="view-card-subtitle">
                Inspect <b>{total_raw_count:,}</b> uncleaned apparel raw material records, category splits, colour distributions, and explore raw SKU codes.
            </div>
            <div class="view-card-meta">
                <div class="view-card-stat">
                    <span>📦</span>
                    <span><b>{total_raw_count:,}</b> Ingested SKUs</span>
                </div>
                <span class="status-indicator {raw_status_class}">{raw_status_label}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "✓ Raw Materials Overview Active" if is_raw_active else "📊 Switch to Raw Materials Overview",
        key="btn_switch_raw",
        use_container_width=True,
        type="primary" if is_raw_active else "secondary",
    ):
        st.session_state["active_view"] = VIEW_RAW
        st.session_state["sidebar_radio_key"] = VIEW_RAW
        st.rerun()

with nav_col2:
    if has_dedup:
        dedup_status_class = "active" if is_dedup_active else "inactive"
        dedup_status_label = "● ACTIVE MODULE" if is_dedup_active else "○ SWITCH TO VIEW"
        dedup_card_class = "view-card active-card" if is_dedup_active else "view-card"

        st.markdown(
            f"""
            <div class="{dedup_card_class}">
                <div class="view-card-top">
                    <div class="view-card-headline">
                        <span>✨</span>
                        <span>Master Deduplication & Clusters</span>
                    </div>
                    <span class="badge-star-feature">⭐ CORE POC ENGINE</span>
                </div>
                <div class="view-card-subtitle">
                    AI/ML clustering & canonical material codes: resolves <b>{dupes_count:,}</b> redundant variations into <b>{total_master_count:,}</b> normalized master SKUs.
                </div>
                <div class="view-card-meta">
                    <div class="view-card-stat" style="color: #c084fc;">
                        <span>⚡</span>
                        <span><b>{reduction_rate:.1f}%</b> SKU Redundancy Reduction</span>
                    </div>
                    <span class="status-indicator {dedup_status_class}">{dedup_status_label}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "✓ Master Deduplication Active" if is_dedup_active else "✨ Switch to Master Deduplication & Clusters",
            key="btn_switch_dedup",
            use_container_width=True,
            type="primary" if is_dedup_active else "secondary",
        ):
            st.session_state["active_view"] = VIEW_DEDUP
            st.session_state["sidebar_radio_key"] = VIEW_DEDUP
            st.rerun()

st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

active_tab = st.session_state["active_view"]

# -----------------------------------------------------------------------------
# TAB 1: Raw Materials Overview (Requested View)
# -----------------------------------------------------------------------------
if active_tab == "📊 Raw Materials Overview":
    st.info(f"ℹ️ **Raw Materials Ingestion View**: You are viewing the raw catalog baseline ({total_raw_count:,} records). To inspect the AI deduplication engine results and canonical master clusters, click **✨ Master Deduplication & Clusters** above.")
    st.subheader("Raw Materials Catalog Metrics")

    # Clean category column for dashboard display
    df_raw["category"] = df_raw["category"].fillna("Uncategorized").replace({"": "Uncategorized"})

    # Summary Metrics Row (Identical Sizing & Modern Styling)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("Total Raw Records", f"{len(df_raw):,}", badge_text="100% Ingested", badge_type="blue", icon="📦")
    with col2:
        render_kpi_card("Unique Categories", str(df_raw["category"].nunique()), badge_text="Partition Isolated", badge_type="purple", icon="🗂️")
    with col3:
        colors_count = df_raw["colour"].nunique() if "colour" in df_raw.columns else 0
        render_kpi_card("Distinct Colours", f"{colors_count:,}", badge_text="Variants Tracked", badge_type="neutral", icon="🎨")
    with col4:
        uom_count = df_raw["inventory_uom"].nunique() if "inventory_uom" in df_raw.columns else 0
        render_kpi_card("Inventory UOMs", str(uom_count), badge_text="Units of Measure", badge_type="neutral", icon="📏")

    st.markdown("---")

    # Charts Row
    col_left, col_right = st.columns(2)

    with col_left:
        cat_counts = df_raw["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Record Count"]
        cat_fig = px.bar(
            cat_counts,
            x="Category",
            y="Record Count",
            title="Materials per Category",
            text="Record Count",
            color="Category",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        cat_fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        cat_fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Number of Items")
        st.plotly_chart(apply_chart_theme(cat_fig), use_container_width=True)

    with col_right:
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

    # Optional Color Distribution Bar Chart
    if "colour" in df_raw.columns:
        top_colors = df_raw["colour"].value_counts().head(10).reset_index()
        top_colors.columns = ["Colour", "Count"]
        color_fig = px.bar(
            top_colors,
            x="Colour",
            y="Count",
            title="Top 10 Most Frequent Colours",
            text="Count",
            color="Count",
            color_continuous_scale="Blues",
        )
        color_fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        st.plotly_chart(apply_chart_theme(color_fig), use_container_width=True)

    st.markdown("---")

    # Filterable Data Table
    st.subheader("Data Explorer")

    col_filter1, col_filter2 = st.columns([1, 2])
    with col_filter1:
        cat_options = ["All"] + sorted([str(c) for c in df_raw["category"].unique()])
        selected_category = st.selectbox("Filter by Category", cat_options)

    with col_filter2:
        search_query = st.text_input("🔍 Search by Material Name or Code", "")

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

    st.caption(f"Displaying **{len(filtered_df):,}** matching rows (showing up to 500 in grid):")
    st.dataframe(filtered_df.head(500), use_container_width=True)

    # CSV Download Option
    csv_bytes = filtered_df.head(1000).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Current View as CSV",
        data=csv_bytes,
        file_name=f"materials_{selected_category.lower()}.csv",
        mime="text/csv",
    )

# -----------------------------------------------------------------------------
# TAB 2: Deduplication & Master Catalog Insights
# -----------------------------------------------------------------------------
elif active_tab == "✨ Master Deduplication & Clusters" and has_dedup:
    st.success(f"🌟 **Core Feature Deliverable**: Normalized Master Materials Catalog & AI Cluster Analytics ({reduction_rate:.1f}% catalog redundancy reduction achieved).")
    st.subheader("Normalized Master Catalog & Deduplication Analytics")

    total_raw = len(df_mapped)
    total_masters = len(df_master)
    dupes_count = int(df_mapped["is_duplicate"].sum())
    reduction = ((total_raw - total_masters) / total_raw * 100) if total_raw else 0.0

    # Summary Metrics Row (Identical Sizing & Modern Styling)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_kpi_card("Total Raw Records", f"{total_raw:,}", badge_text="Source Catalog", badge_type="neutral", icon="📦")
    with m2:
        render_kpi_card("Normalized Master Codes", f"{total_masters:,}", badge_text=f"↓ {total_raw - total_masters:,} SKUs", badge_type="green", icon="🏷️")
    with m3:
        render_kpi_card("Duplicates Consolidating", f"{dupes_count:,}", badge_text="Resolved Variants", badge_type="purple", icon="🔀")
    with m4:
        render_kpi_card("Redundancy Reduction", f"{reduction:.2f}%", badge_text="⚡ High Compression", badge_type="green", icon="📈")

    st.markdown("---")

    col_m_left, col_m_right = st.columns(2)
    with col_m_left:
        # Category breakdown of master codes
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

    with col_m_right:
        # Largest Duplicate Clusters
        top_clusters = df_master.sort_values(by="cluster_record_count", ascending=False).head(10)
        fig_cluster = px.bar(
            top_clusters,
            x="cluster_record_count",
            y="canonical_material_name",
            orientation="h",
            title="Top 10 Largest Duplicate Clusters",
            labels={"cluster_record_count": "Raw Variations in Cluster", "canonical_material_name": "Canonical Name"},
            color="cluster_record_count",
            color_continuous_scale="Reds",
        )
        fig_cluster.update_layout(yaxis={"autorange": "reversed"})
        st.plotly_chart(apply_chart_theme(fig_cluster), use_container_width=True)


    st.subheader("Master Catalog Explorer (`master_materials`)")
    st.dataframe(df_master, use_container_width=True)

    st.subheader("Raw Item Tracking with Foreign Key (`material_records_mapped`)")
    selected_master = st.selectbox(
        "Drill down into a Master Code to inspect grouped variants:",
        options=df_master["new_master_code"].tolist(),
        format_func=lambda code: f"{code} — {df_master.loc[df_master['new_master_code'] == code, 'canonical_material_name'].values[0]}",
    )

    cluster_variants = df_mapped[df_mapped["new_master_code"] == selected_master]
    st.write(f"Found **{len(cluster_variants)}** raw entries mapped to **{selected_master}**:")
    st.dataframe(cluster_variants, use_container_width=True)
