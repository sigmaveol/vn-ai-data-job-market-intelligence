# Huong Dan Deploy Cloud

Khuyen nghi dung Streamlit Cloud cho demo mon hoc vi nhanh, mien phi, va hop voi dashboard Streamlit.

## 1. Chuan bi GitHub

Push thu muc `Project/` len GitHub repository.

Can dam bao cac file sau co trong repo:

```text
app.py
pages/
utils/
src/
data/processed/jobs_processed.csv
requirements.txt
runtime.txt
.streamlit/config.toml
.streamlit/secrets.example.toml
```

Khong commit file:

```text
.env
.streamlit/secrets.toml
```

## 2. Deploy bang Streamlit Cloud

1. Vao `https://share.streamlit.io`.
2. Dang nhap bang GitHub.
3. Chon `New app`.
4. Chon repository cua project.
5. Branch: `main`.
6. Main file path:

```text
app.py
```

Neu repo chua truc tiep nam trong thu muc `Project`, dat main file path la:

```text
Project/app.py
```

7. Bam `Deploy`.

## 3. Cau hinh secrets tren Streamlit Cloud

Trong app Streamlit Cloud, vao `Settings -> Secrets`.

Public demo, chua bat OAuth:

```toml
APP_ENV = "production"
APP_BASE_URL = "https://your-app.streamlit.app"
AUTH_ENABLED = "false"
LOG_LEVEL = "INFO"
USER_ROLE_MAP = "{}"
DEFAULT_AUTH_ROLE = "viewer"
```

Protected demo co OAuth Google:

```toml
APP_ENV = "production"
APP_BASE_URL = "https://your-app.streamlit.app"
AUTH_ENABLED = "true"
LOG_LEVEL = "INFO"

GOOGLE_OAUTH_CLIENT_ID = "your-google-client-id"
GOOGLE_OAUTH_CLIENT_SECRET = "your-google-client-secret"
GOOGLE_OAUTH_REDIRECT_URI = "https://your-app.streamlit.app"

USER_ROLE_MAP = '{"your-email@gmail.com":"admin"}'
DEFAULT_AUTH_ROLE = "viewer"
```

Sau khi sua secrets, bam `Reboot app`.

## 4. Deploy bang Render

Render da co file:

```text
render.yaml
```

Cach lam:

1. Push repo len GitHub.
2. Vao `https://render.com`.
3. Chon `New -> Blueprint`.
4. Chon GitHub repository.
5. Render se doc `render.yaml`.
6. Them environment variables neu can OAuth.
7. Deploy.

## 5. OAuth Google

Can vao Google Cloud Console:

1. Tao OAuth Client ID loai `Web application`.
2. Them Authorized redirect URI:

```text
https://your-app.streamlit.app
```

hoac URL Render:

```text
https://your-render-app.onrender.com
```

3. Copy Client ID va Client Secret vao Streamlit Secrets/Render Environment Variables.

## 6. Kiem tra sau deploy

- Trang Overview load du lieu thanh cong.
- Sidebar filters hoat dong.
- Salary/Skills/Company/Geographic/Timeseries pages mo duoc.
- Resume Analyzer chi mo duoc voi role `analyst` hoac `admin`.
- AI Agent Automation chi mo duoc voi role `analyst` hoac `admin`.
- CSV export hoat dong.
- Neu bat OAuth: login/logout hoat dong.

## 7. Loi thuong gap

Neu app loi `ModuleNotFoundError`, kiem tra package trong `requirements.txt`.

Neu app khong thay dataset, kiem tra file:

```text
data/processed/jobs_processed.csv
```

Neu OAuth login xong quay lai loi, kiem tra:

```text
APP_BASE_URL
GOOGLE_OAUTH_REDIRECT_URI
Authorized redirect URI trong Google Cloud Console
```
