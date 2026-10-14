"""제조 품질 현황 대시보드 (Streamlit)

실행 방법: streamlit run app.py
"""

import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# 0. 기본 설정
# ----------------------------------------------------------------------
st.set_page_config(page_title="제조 품질 현황 대시보드", page_icon="🏭", layout="wide")

# CSV에 반드시 있어야 하는 컬럼
REQUIRED_COLUMNS = ["inspection_date", "product_id", "result", "defect_type", "confidence"]


# ----------------------------------------------------------------------
# 1. 데이터 준비 함수
# ----------------------------------------------------------------------
def make_sample_data(n_rows=300):
    """CSV를 올리지 않아도 테스트할 수 있도록 샘플 데이터를 코드에서 만든다."""
    rng = np.random.default_rng(42)  # 시드를 고정해서 항상 같은 데이터가 나오게 한다
    dates = pd.date_range("2026-10-01", periods=14).to_numpy()

    df = pd.DataFrame(
        {
            "inspection_date": rng.choice(dates, size=n_rows),
            "product_id": rng.choice(["P001", "P002", "P003", "P004", "P005"], size=n_rows),
            "result": rng.choice(["OK", "NG"], size=n_rows, p=[0.88, 0.12]),
        }
    )

    # NG인 행에만 불량 유형을 넣고, OK는 "None"으로 둔다
    df["defect_type"] = "None"
    is_ng = df["result"] == "NG"
    df.loc[is_ng, "defect_type"] = rng.choice(
        ["Scratch", "Crack", "Dent", "Stain"], size=int(is_ng.sum())
    )

    # 신뢰도(confidence): OK는 높게, NG는 조금 낮게
    df["confidence"] = np.where(
        is_ng,
        rng.uniform(0.80, 0.95, size=n_rows),
        rng.uniform(0.93, 0.99, size=n_rows),
    ).round(2)

    return df.sort_values("inspection_date").reset_index(drop=True)


def load_csv(file):
    """업로드된 CSV를 읽는다. 한글 윈도우 엑셀 CSV(cp949)도 읽을 수 있게 처리한다."""
    try:
        return pd.read_csv(file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, encoding="cp949")


def clean_data(df):
    """컬럼 확인 및 자료형 정리. 필수 컬럼이 없으면 (None, 없는 컬럼 목록)을 돌려준다."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return None, missing

    df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
    df = df.dropna(subset=["inspection_date"])  # 날짜를 읽을 수 없는 행은 제외

    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["result"] = df["result"].astype(str).str.strip().str.upper()
    # CSV의 "None"은 pandas가 빈 값(NaN)으로 읽는 경우가 있어서 다시 "None" 문자열로 통일
    df["defect_type"] = df["defect_type"].fillna("None").astype(str).str.strip()
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    return df, []


# ----------------------------------------------------------------------
# 2. 사이드바: CSV 업로드
# ----------------------------------------------------------------------
st.sidebar.header("🔧 설정")
uploaded_file = st.sidebar.file_uploader("CSV 파일 업로드", type=["csv"])

if uploaded_file is not None:
    try:
        raw_df = load_csv(uploaded_file)
    except Exception as e:
        st.error(f"CSV 파일을 읽지 못했습니다: {e}")
        st.stop()
else:
    raw_df = make_sample_data()

data, missing_columns = clean_data(raw_df)
if data is None:
    st.error(f"필수 컬럼이 없습니다: {', '.join(missing_columns)}")
    st.write("필요한 컬럼:", ", ".join(REQUIRED_COLUMNS))
    st.stop()
if data.empty:
    st.error("사용할 수 있는 데이터가 없습니다. 날짜 형식을 확인해 주세요.")
    st.stop()

# ----------------------------------------------------------------------
# 3. 사이드바: 필터 (날짜 / 제품 / 검사 결과)
# ----------------------------------------------------------------------
min_date = data["inspection_date"].min().date()
max_date = data["inspection_date"].max().date()

date_range = st.sidebar.date_input(
    "날짜 필터", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
# 날짜를 하나만 고른 경우(시작일만 선택)에도 오류가 나지 않게 처리
if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

product_options = sorted(data["product_id"].unique())
selected_products = st.sidebar.multiselect("제품 필터", product_options, default=product_options)

selected_results = st.sidebar.multiselect("검사 결과 필터", ["OK", "NG"], default=["OK", "NG"])

# 필터 적용
date_only = data["inspection_date"].dt.date
mask = (
    (date_only >= start_date)
    & (date_only <= end_date)
    & (data["product_id"].isin(selected_products))
    & (data["result"].isin(selected_results))
)
filtered = data[mask]

# ----------------------------------------------------------------------
# 4. 화면 상단: 제목 + 데이터 미리보기
# ----------------------------------------------------------------------
st.title("제조 품질 현황 대시보드")
st.caption("AI 비전검사 PoC 준비를 위한 품질 데이터 모니터링")

if uploaded_file is None:
    st.info("업로드된 CSV가 없어 **샘플 데이터**로 표시 중입니다. 왼쪽 사이드바에서 CSV를 올릴 수 있습니다.")

with st.expander("📂 데이터 미리보기 (상위 5건)", expanded=uploaded_file is not None):
    st.dataframe(raw_df.head(5), hide_index=True)
    st.caption(f"전체 {len(raw_df):,}행 × {len(raw_df.columns)}열")

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 사이드바의 필터를 조정해 주세요.")
    st.stop()

# ----------------------------------------------------------------------
# 5. KPI 카드
# ----------------------------------------------------------------------
total_count = len(filtered)
ok_count = int((filtered["result"] == "OK").sum())
ng_count = int((filtered["result"] == "NG").sum())
defect_rate = ng_count / total_count * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 검사", f"{total_count:,}건")
col2.metric("정상 (OK)", f"{ok_count:,}건")
col3.metric("불량 (NG)", f"{ng_count:,}건")
col4.metric("불량률", f"{defect_rate:.1f}%")

st.divider()

# ----------------------------------------------------------------------
# 6. 중단: 날짜별 그래프 / 불량 유형별 그래프
# ----------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("날짜별 검사 현황 (OK / NG)")
    daily = (
        filtered.groupby([filtered["inspection_date"].dt.date, "result"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["OK", "NG"], fill_value=0)
    )
    daily.index = pd.to_datetime(daily.index)
    st.line_chart(daily, color=["#2E86DE", "#E74C3C"])  # OK=파랑, NG=빨강

with right:
    st.subheader("불량 유형별 건수")
    defect_counts = filtered[
        (filtered["result"] == "NG") & (filtered["defect_type"] != "None")
    ]["defect_type"].value_counts()

    if defect_counts.empty:
        st.info("표시할 불량 데이터가 없습니다.")
    else:
        st.bar_chart(defect_counts)

st.divider()

# ----------------------------------------------------------------------
# 7. 하단: 최근 검사 결과 10건
# ----------------------------------------------------------------------
st.subheader("최근 검사 데이터 (10건)")

recent = filtered.sort_values("inspection_date", ascending=False).head(10).copy()
recent["inspection_date"] = recent["inspection_date"].dt.strftime("%Y-%m-%d")
# OK / NG를 아이콘으로 구분
recent["result"] = recent["result"].map({"OK": "🟢 OK", "NG": "🔴 NG"}).fillna(recent["result"])

st.dataframe(recent[REQUIRED_COLUMNS], hide_index=True)
