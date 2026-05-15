# Job Market Intelligence & Resume Matching System
**Phân tích Thị trường AI/Data Việt Nam 2026**

> Môn học: Phân tích Dữ liệu và Trực quan hóa (505067) — Trường Đại học Tôn Đức Thắng  
> Nhóm: Hoàng Sinh Hưng (52300106) · Trần Thiên Hưng (52300109) · HK2, 2025–2026

**🌐 Dashboard trực tuyến:**
[https://vn-ai-data-job-market-intelligence-qtagmjab5appvhhgqqphbke.streamlit.app](https://vn-ai-data-job-market-intelligence-qtagmjab5appvhhgqqphbke.streamlit.app)

---

## Giới thiệu

Đề tài thu thập và phân tích **7.051 tin tuyển dụng** trong lĩnh vực AI và Khoa học Dữ liệu tại Việt Nam từ 6 nền tảng lớn (123job, VietnamWorks, ITviec, TopDev, TopCV, CareerViet) trong giai đoạn tháng 1–5/2026. Sản phẩm gồm:

- **Dashboard Streamlit** — 8 trang phân tích tương tác với bộ lọc đồng bộ
- **Hệ thống đối chiếu hồ sơ** — tải lên CV, nhận điểm tương thích và gợi ý cải thiện
- **Báo cáo học thuật** — 8 chương, ~60 trang, kèm 16 biểu đồ
- **Slide thuyết trình** — 24 trang

---

## Kết quả nổi bật

| Chỉ số | Giá trị |
|---|---|
| Tổng tin tuyển dụng | 7.051 (từ 3.496 doanh nghiệp) |
| Lương trung vị | 980 USD/tháng (~25 triệu VND) |
| Tỷ lệ công bố lương | 42% |
| Kỹ năng dẫn đầu | Python (1.282 tin) · SQL (1.199 tin) |
| Thị trường tập trung | Hà Nội 46% · TP.HCM 38% |
| Lương cao nhất | MLOps/DevOps · Cloud Engineer (>1.200 USD) |

---

## Cài đặt và chạy

**Yêu cầu:** Python 3.9+

```bash
# 1. Cài thư viện
pip install -r requirements.txt

# 2. Chạy dashboard
streamlit run app.py
```

Mở trình duyệt tại `http://localhost:8501`

---

## Cấu trúc dự án

```
Project/
├── app.py                       # Entry point — trang Tổng quan
├── pages/                       # 8 trang phân tích
│   ├── 1_Salary.py              # Phân tích lương
│   ├── 2_Skills.py              # Phân tích kỹ năng
│   ├── 3_Company.py             # Phân tích công ty
│   ├── 4_Geographic.py          # Phân tích địa lý
│   ├── 5_Timeseries.py          # Xu hướng tuyển dụng
│   ├── 6_Resume.py              # Đối chiếu hồ sơ ứng viên
│   ├── 7_About.py               # Thông tin đề tài
│   └── 8_Export.py              # Xuất dữ liệu
├── utils/                       # Tiện ích dùng chung
├── src/
│   ├── crawler/                 # Thu thập dữ liệu 6 nền tảng
│   ├── preprocessing/           # Làm sạch và chuẩn hóa
│   ├── nlp/                     # Trích xuất kỹ năng
│   └── resume_analyzer/         # Đối chiếu hồ sơ ứng viên
├── data/
│   └── processed/
│       └── jobs_processed.parquet   # Bộ dữ liệu chính (7.051 bản ghi)
├── notebooks/                   # 3 Jupyter Notebook
├── outputs/
│   ├── charts/                  # 16 biểu đồ EDA
│   ├── reports/final_report.docx
│   └── slides/*.pptx
└── requirements.txt
```

---

## Tài liệu

| File | Mô tả |
|---|---|
| `outputs/reports/final_report.docx` | Báo cáo đầy đủ 8 chương |
| `outputs/slides/*.pptx` | Slide thuyết trình 24 trang |
| `notebooks/02_eda.ipynb` | Notebook phân tích EDA chính |
| `notebooks/01_data_collection.ipynb` | Quy trình thu thập dữ liệu |
