"""Centralized styling — CSS injection and Plotly theme."""
import streamlit as st

# ── Color palette ──────────────────────────────────────────────────────────────
C = {
    'bg':      '#f6f8fc',
    'surface': '#ffffff',
    'card':    '#ffffff',
    'border':  '#dbe3ef',
    'accent':  '#2563eb',
    'red':     '#e11d48',
    'green':   '#059669',
    'orange':  '#ea580c',
    'blue':    '#0284c7',
    'purple':  '#7c3aed',
    'text':    '#0f172a',
    'muted':   '#64748b',
}

COLORWAY = [C['accent'], C['red'], C['green'], C['orange'], C['blue'], C['purple'],
            '#ffd166', '#a8edea', '#f9ca24', '#6ab04c']

SEQUENTIAL = 'Viridis'

# ── Plotly layout defaults ─────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color=C['text'], family='Segoe UI, system-ui, sans-serif', size=12),
    margin=dict(t=40, b=50, l=60, r=20),
    colorway=COLORWAY,
    hoverlabel=dict(bgcolor=C['card'], bordercolor=C['accent'], font_color=C['text']),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor=C['border'], font_color=C['text']),
    xaxis=dict(gridcolor=C['border'], zerolinecolor=C['border'], tickfont_color=C['muted']),
    yaxis=dict(gridcolor=C['border'], zerolinecolor=C['border'], tickfont_color=C['muted']),
)

PLOTLY_CONFIG = dict(
    displayModeBar=True,
    modeBarButtonsToRemove=['select2d','lasso2d','autoScale2d','toggleSpikelines'],
    displaylogo=False,
    toImageButtonOptions=dict(format='png', scale=2),
)


def apply_layout(fig, height: int = 340, title: str = ''):
    fig.update_layout(**PLOTLY_LAYOUT, height=height, title=title)
    return fig


# ── CSS injection ──────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
:root {
    --app-bg: #f6f8fc;
    --surface: #ffffff;
    --card: #ffffff;
    --border: #dbe3ef;
    --accent: #2563eb;
    --accent-soft: #dbeafe;
    --text: #0f172a;
    --muted: #64748b;
    --green: #059669;
    --orange: #ea580c;
}
/* Hide default streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.stApp { background: var(--app-bg); color: var(--text); }

/* Main content padding */
.block-container {padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1440px;}

/* KPI metric cards */
[data-testid="metric-container"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    border-top: 3px solid var(--accent);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    min-height: 112px;
}
[data-testid="metric-container"] > div { gap: 4px; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 12px !important; }
[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-size: clamp(18px, 2vw, 24px) !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* Insight panel */
.insight-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 10px;
    padding: 20px 24px;
    margin-top: 16px;
    font-size: 14px;
    line-height: 1.8;
}
.insight-panel h4 {
    color: var(--accent);
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0 0 12px 0;
}
.insight-panel ul { margin: 8px 0; padding-left: 20px; }
.insight-panel li { margin-bottom: 6px; color: var(--text); }
.insight-panel .highlight { color: var(--green); font-weight: 600; }
.insight-panel .warn { color: var(--orange); font-weight: 600; }

/* Chart cards */
.chart-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0;
    overflow: hidden;
}

/* Page header */
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 22px; font-weight: 700; margin: 0; }
.page-header p { color: var(--muted); font-size: 13px; margin: 4px 0 0 0; }

.empty-state {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 4px solid var(--orange);
    border-radius: 8px;
    padding: 20px 22px;
    margin: 16px 0;
}
.empty-state h4 { color: var(--orange); margin: 0 0 6px; font-size: 15px; }
.empty-state p { color: var(--muted); margin: 0; font-size: 14px; }

/* Filter tag */
.filter-tag {
    display: inline-block;
    background: var(--accent-soft);
    border: 1px solid #bfdbfe;
    color: var(--accent);
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    margin: 2px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label {
    color: var(--muted) !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.sidebar-status {
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
}
.sidebar-status strong { color: var(--text); font-size: 22px; line-height: 1; }
.sidebar-status span { color: var(--muted); font-size: 12px; margin-left: 4px; }
.sidebar-status p { color: var(--muted); font-size: 11px; margin: 6px 0 0; }

/* Divider */
hr { border-color: var(--border) !important; }

/* Tag cloud */
.skill-tag {
    display: inline-block;
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 12px;
    margin: 3px;
    cursor: default;
    transition: all 0.15s;
}

/* Export controls */
[data-testid="stDownloadButton"] button {
    border-radius: 8px;
    border-color: var(--border);
}

@media (max-width: 900px) {
    .block-container {padding-left: 0.85rem; padding-right: 0.85rem;}
    .page-header h1 {font-size: 20px;}
    .page-header p {font-size: 12px;}
    [data-testid="metric-container"] {min-height: 96px; padding: 12px 14px;}
    .insight-panel {padding: 16px 18px;}
}
</style>
""", unsafe_allow_html=True)


def insight_panel(html_content: str):
    st.markdown(f'<div class="insight-panel"><h4>Phân Tích & Nhận Xét</h4>{html_content}</div>',
                unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ''):
    st.markdown(f'<div class="page-header"><h1>{title}</h1><p>{subtitle}</p></div>',
                unsafe_allow_html=True)


def empty_state(title: str = "Không có dữ liệu", message: str = "Hãy điều chỉnh hoặc xóa bộ lọc trong sidebar."):
    st.markdown(
        f'<div class="empty-state"><h4>{title}</h4><p>{message}</p></div>',
        unsafe_allow_html=True,
    )
