"""About & Methodology page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Về Dự Án", page_icon="ℹ", layout="wide")

from utils.style import inject_css, page_header
from utils.data_loader import load_data, get_skill_counts, dataset_summary
from utils.sidebar import render_sidebar

inject_css()
render_sidebar()

df = load_data()
summary = dataset_summary(df)
skill_count = len(get_skill_counts(df))

page_header("ℹ Về Dự Án & Phương Pháp Luận",
            "Data Analysis and Visualization (505067) — Học kỳ 2/2025–2026")

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown(f"""
    ### Tổng Quan Dự Án

    **Job Market Intelligence & Resume Matching System** là hệ thống phân tích thị trường tuyển dụng
    AI/Data tại Việt Nam, được xây dựng trong khuôn khổ môn học **Data Analysis and Visualization (505067)**.

    Hệ thống thu thập, xử lý và trực quan hóa dữ liệu tuyển dụng từ 6 nền tảng lớn, cung cấp
    insights có giá trị cho sinh viên, ứng viên, và nhà tuyển dụng.

    ---

    ### Nguồn Dữ Liệu

    | Nền tảng | Phương pháp thu thập | Số tin |
    |---|---|---|
    | **123job** | Selenium scraping | ~4.100 |
    | **VietnamWorks** | REST API | ~1.170 |
    | **ITviec** | JSON-LD + Selenium | ~800 |
    | **TopDev** | JSON-LD parsing | ~108 |
    | **TopCV** | Selenium (Cloudflare limited) | ~500 |
    | **CareerViet** | Selenium scraping | ~373 |
    | **Tổng** | | **{summary['jobs']:,} tin unique** |

    ---

    ### Pipeline Xử Lý Dữ Liệu

    ```
    Thu thập dữ liệu thô (Phase 2)
        → Dedup + Normalize (Phase 3)
        → Phân tích EDA (Phase 4)
        → Dashboard interactive (Phase 5)
        → NLP & Resume Analyzer (Phase 6)
    ```

    **Tiêu chí làm sạch:**
    - Loại bỏ tin trùng lặp theo job hash (tiêu đề + công ty + ngày)
    - Chuẩn hóa mức lương về USD (tỷ giá VND 25.500/USD)
    - Chuẩn hóa địa điểm về tên tỉnh/thành phố chuẩn
    - Suy luận cấp độ kinh nghiệm từ tiêu đề và mô tả
    - Lọc outlier lương (> $10.000 USD/tháng)

    ---

    ### Phân Loại Vai Trò

    Sử dụng keyword matching trên tiêu đề công việc để phân loại vào 10 nhóm:
    Data Analyst, Business Analyst, Data Engineer, AI/ML Engineer,
    Data Scientist, MLOps/DevOps, Software Engineer, Manager/Lead, Database/DBA, Intern/Fresher.

    ---

    ### Hạn Chế

    - **Thiên lệch nguồn**: 123job chiếm 58% → ảnh hưởng phân phối
    - **Thiếu mô tả TopCV**: Cloudflare chặn ~75% request
    - **Lương không công bố**: 58% tin không có mức lương cụ thể
    - **Cửa sổ thời gian ngắn**: 5 tháng (Jan–May 2026)
    """)

with col2:
    st.markdown(f"""
    ### Nhóm Thực Hiện

    ---

    **Hoàng Sinh Hưng**
    MSSV: 52300106

    **Trần Thiên Hưng**
    MSSV: 52300109

    ---

    ### Môn Học

    **Data Analysis and Visualization**
    Mã môn: 505067
    Học kỳ 2 / 2025–2026

    ---

    ### Tech Stack

    **Thu thập dữ liệu:**
    Python · Selenium · Requests
    BeautifulSoup · JSON-LD

    **Xử lý dữ liệu:**
    Pandas · NumPy · Parquet

    **Trực quan hóa:**
    Plotly · Streamlit
    Matplotlib · Seaborn

    **Dashboard:**
    Streamlit · Plotly.js
    HTML/CSS/JavaScript

    ---

    ### Thống Kê Dataset

    | Chỉ số | Giá trị |
    |---|---|
    | Tổng tin | {summary['jobs']:,} |
    | Doanh nghiệp | {summary['companies']:,} |
    | Tỉnh/TP | {summary['cities']:,} |
    | Nguồn tuyển dụng | {summary['sources']:,} |
    | Cột dữ liệu | {len(df.columns):,} |
    | Có mức lương | {summary['salary_coverage']:.1f}% |
    | Kỹ năng unique | {skill_count:,} |

    ---

    ### Khoảng Thời Gian

    **Tháng 1 – 5/2026**
    Bao gồm giai đoạn Tết Nguyên Đán
    và phục hồi sau Tết

    """)
