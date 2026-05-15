"""Sidebar filter panel — renders on every page, updates session_state."""
import streamlit as st
from src.auth import logout_button, require_login
from utils.data_loader import apply_filters, dataset_summary, load_data, EXP_ORDER


def render_sidebar():
    """Render filter sidebar. Call at top of each page."""
    require_login()
    df = load_data()

    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 16px">
            <div style="font-size:16px;font-weight:700;color:#6c63ff">🇻🇳 VN Job Market</div>
            <div style="font-size:11px;color:#9098b1;margin-top:2px">AI/Data Intelligence · 2026</div>
        </div>
        """, unsafe_allow_html=True)
        logout_button()
        st.divider()

        st.markdown('<p style="font-size:11px;color:#9098b1;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">Bộ Lọc</p>', unsafe_allow_html=True)

        # City
        all_cities = sorted(df['city'].value_counts().head(20).index.tolist())
        cities = st.multiselect('Thành phố', all_cities, default=[], key='f_cities')

        # Role
        all_roles = sorted(df['role_category'].value_counts().index.tolist())
        roles = st.multiselect('Vai trò', all_roles, default=[], key='f_roles')

        # Experience
        exp_opts = [e for e in EXP_ORDER if e in df['experience_level_inferred'].values]
        exps = st.multiselect('Cấp độ kinh nghiệm', exp_opts, default=[], key='f_exps')

        # Source
        all_srcs = sorted(df['source_website'].dropna().unique().tolist())
        sources = st.multiselect('Nguồn tuyển dụng', all_srcs, default=[], key='f_srcs')

        # Remote
        remote = st.selectbox('Hình thức làm việc', ['Tất cả', 'Remote', 'Onsite'], key='f_remote')

        # Salary range
        sal_max = int(df['salary_midpoint_usd'].quantile(0.99) if df['salary_midpoint_usd'].notna().any() else 5000)
        sal_range = st.slider('Mức lương (USD/tháng)', 0, sal_max, (0, sal_max), step=100, key='f_sal')

        st.checkbox(
            'Bật nút tải PNG',
            value=False,
            key='enable_png_exports',
            help='Tắt mặc định để dashboard tải nhanh hơn; có thể dùng nút camera trên Plotly modebar.',
        )

        st.divider()

        if st.button('Xóa bộ lọc', width='stretch'):
            for k in ['f_cities','f_roles','f_exps','f_srcs','f_remote','f_sal']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        # Save filters
        filters = {
            'cities': cities, 'roles': roles, 'exps': exps,
            'sources': sources, 'remote': remote, 'salary_range': sal_range,
        }
        st.session_state['filters'] = filters

        filtered = apply_filters(df, filters)
        summary = dataset_summary(filtered)

        st.divider()
        st.markdown(
            '<p style="font-size:11px;color:#9098b1;text-transform:uppercase;'
            'letter-spacing:1px;margin-bottom:8px">Trạng thái dữ liệu</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="sidebar-status">
                <div><strong>{summary['jobs']:,}</strong><span>/{len(df):,} tin</span></div>
                <p>{summary['companies']:,} công ty · {summary['cities']:,} tỉnh/TP</p>
                <p>{summary['salary_coverage']:.1f}% tin có công bố lương</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(
            '<div style="font-size:11px;color:#555;line-height:1.6">'
            'Hoàng Sinh Hưng (52300106)<br>Trần Thiên Hưng (52300109)<br>'
            '<span style="color:#6c63ff">Data Analysis 505067</span></div>',
            unsafe_allow_html=True
        )


def create_sidebar():
    """Compatibility wrapper for dashboard builders."""
    return render_sidebar()
