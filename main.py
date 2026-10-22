
# main.py
# KOBIS 공식 API로 날짜별 박스오피스를 보여 주는 영화관 테마 대시보드입니다.

import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="오늘의 스크린 | 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# 2. 영화관 느낌의 어두운 배경과 시네마 레드 스타일
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(ellipse at 50% -15%, #3b1018 0%, #111116 38%, #09090c 78%);
        color: #f5f5f7;
    }
    [data-testid="stHeader"] { background: rgba(9, 9, 12, .7); }
    .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: #fff !important; letter-spacing: -.025em; }
    p, label, [data-testid="stCaptionContainer"] { color: #b8b8c2; }
    .cinema-hero {
        padding: 28px 30px; margin: 2px 0 22px; border: 1px solid #70232d;
        border-radius: 20px; background: linear-gradient(115deg, #390d14, #17171e 68%);
        box-shadow: 0 16px 42px #0005;
    }
    .cinema-kicker { color: #f5c76b; font-size: .78rem; font-weight: 800;
        letter-spacing: .2em; margin-bottom: 8px; }
    .cinema-title { color: #fff; font-size: clamp(1.8rem, 4vw, 2.8rem);
        font-weight: 900; line-height: 1.15; margin-bottom: 10px; }
    .cinema-subtitle { color: #d0cbd0; margin: 0; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #2b191e, #14141a); border: 1px solid #63212a;
        border-top: 3px solid #e50914; border-radius: 15px; padding: 18px 20px;
        box-shadow: 0 10px 26px #0004;
    }
    [data-testid="stMetricLabel"] { color: #c9c2c7 !important; }
    [data-testid="stMetricValue"] { color: #fff !important; font-weight: 850 !important; }
    [data-testid="stDateInput"] input { color: #fff !important; background: #19151a !important;
        border-color: #71303a !important; border-radius: 10px !important; }
    [data-testid="stDataFrame"] { border: 1px solid #3b2a30; border-radius: 13px; overflow: hidden; }
    hr { border-color: #e509144d !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. 한국 시간 기준으로 오늘과 어제를 계산합니다. 서버 시간대는 사용하지 않습니다.
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
yesterday = today_kst - datetime.timedelta(days=1)

# 4. KOBIS 일별 박스오피스 API 주소
API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
)


@st.cache_data(ttl=1800)
def fetch_boxoffice(date_str: str, api_key: str):
    """선택한 날짜의 박스오피스 JSON 데이터를 가져옵니다."""
    response = requests.get(
        API_URL,
        params={"key": api_key, "targetDt": date_str},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def rank_change_label(value: int) -> str:
    """순위 변동 숫자를 화살표와 함께 표시합니다."""
    if value > 0:
        return f"↑ +{value}"
    if value < 0:
        return f"↓ {value}"
    return "—"


def rank_change_style(value: str) -> str:
    """순위 상승은 빨간색, 하락은 파란색으로 표시합니다."""
    if isinstance(value, str) and value.startswith("↑"):
        return "color: #ff4d57; font-weight: bold;"
    if isinstance(value, str) and value.startswith("↓"):
        return "color: #62a5ff; font-weight: bold;"
    return "color: #a1a1aa;"


# 5. 영화관 분위기의 제목 영역
st.markdown(
    """
    <div class="cinema-hero">
      <div class="cinema-kicker">THE DAILY BOX OFFICE</div>
      <div class="cinema-title">🎬 오늘의 스크린</div>
      <p class="cinema-subtitle">날짜별 흥행 순위와 관객 흐름을 한눈에 확인하세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 오늘은 아직 집계 전이므로 달력에서 어제까지만 고를 수 있습니다.
selected_date = st.date_input(
    "🎟️ 상영일 선택", value=yesterday, max_value=yesterday, format="YYYY-MM-DD"
)
selected_date_text = selected_date.strftime("%Y년 %m월 %d일")
target_dt = selected_date.strftime("%Y%m%d")
st.caption(f"선택한 상영일: {selected_date_text} · 한국 시간 기준")
st.divider()

# 6. API 인증키는 Secrets에서만 읽습니다. 코드에 실제 키를 작성하지 마세요.
try:
    api_key = str(st.secrets["KOBIS_KEY"]).strip()
    if not api_key:
        st.error("KOBIS_KEY가 비어 있습니다.")
        st.info('앱 설정 → Secrets에 KOBIS_KEY = "발급받은_실제_인증키"를 등록해 주세요.')
        st.stop()
except (KeyError, FileNotFoundError):
    st.error("KOBIS API 인증키를 찾을 수 없습니다.")
    st.info('앱 설정 → Secrets에 KOBIS_KEY = "발급받은_실제_인증키"를 등록해 주세요.')
    st.stop()

# 7. API를 호출하고 네트워크 오류를 한국어로 안내합니다.
try:
    data = fetch_boxoffice(target_dt, api_key)
except requests.exceptions.Timeout:
    st.error("KOBIS API 응답 시간이 초과되었습니다.")
    st.info("잠시 후 다시 시도하고 네트워크와 KOBIS 서버 상태를 확인해 주세요.")
    st.stop()
except requests.exceptions.HTTPError as exc:
    st.error("KOBIS 서버에서 HTTP 오류가 발생했습니다.")
    st.caption(f"오류 정보: {exc}")
    st.info("API 주소와 KOBIS 서버 상태를 확인해 주세요.")
    st.stop()
except requests.exceptions.RequestException as exc:
    st.error("KOBIS API에 연결하지 못했습니다.")
    st.caption(f"오류 정보: {exc}")
    st.info("인터넷 연결, API 주소, 서버 상태를 확인해 주세요.")
    st.stop()
except ValueError:
    st.error("API 응답을 JSON으로 읽을 수 없습니다.")
    st.info("KOBIS 서버의 응답 상태를 확인한 뒤 다시 시도해 주세요.")
    st.stop()

# 8. HTTP 200 응답이어도 faultInfo가 있으면 API 자체 오류입니다.
if not isinstance(data, dict):
    st.error("API 응답 형식이 예상과 다릅니다.")
    st.info("KOBIS API 응답 구조를 확인해 주세요.")
    st.stop()

if "faultInfo" in data:
    fault = data.get("faultInfo") or {}
    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "코드 없음")
        error_message = fault.get("message", "오류 메시지 없음")
    else:
        error_code, error_message = "코드 없음", str(fault)
    st.error("KOBIS API에서 오류 응답을 반환했습니다.")
    st.write(f"오류 코드: {error_code}")
    st.write(f"오류 메시지: {error_message}")
    st.info("Secrets의 KOBIS_KEY가 정확하고 사용 가능한 인증키인지 확인해 주세요.")
    st.stop()

# 9. 응답에서 영화 목록을 확인합니다.
boxoffice_result = data.get("boxOfficeResult")
if not isinstance(boxoffice_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info("선택한 날짜와 KOBIS API 응답 구조를 확인해 주세요.")
    st.stop()

movie_list = boxoffice_result.get("dailyBoxOfficeList")
if not isinstance(movie_list, list) or not movie_list:
    st.warning("그날은 아직 집계 전입니다")
    st.info(
        "선택한 날짜의 영화 목록이 비어 있습니다. 집계 자료가 아직 제공되지 않았거나 "
        "해당 날짜의 결과가 없을 수 있으니 KOBIS 공식 사이트에서도 확인해 주세요."
    )
    st.stop()

# 10. API 숫자는 문자열이므로 계산을 위해 정수로 변환합니다.
df = pd.DataFrame(movie_list)
for column in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    else:
        df[column] = 0

for column in ["movieNm", "openDt"]:
    if column not in df.columns:
        df[column] = ""
    df[column] = df[column].fillna("").astype(str)

# 누적 관객수가 100만 명을 초과한 영화명에는 트로피를 표시합니다.
def add_trophy(row):
    return f"🏆 {row['movieNm']}" if row["audiAcc"] > 1_000_000 else row["movieNm"]


df["displayMovieNm"] = df.apply(add_trophy, axis=1)

# 11. 1위 영화와 지표 카드 3개
first_place = df[df["rank"] == 1]
first_movie = (
    first_place.iloc[0]
    if not first_place.empty
    else df.sort_values("audiCnt", ascending=False).iloc[0]
)

st.subheader("🏆 흥행 1위")
st.markdown(f"### {first_movie['displayMovieNm']}")
card1, card2, card3 = st.columns(3)
with card1:
    st.metric("🎟️ 당일 관객수", f"{first_movie['audiCnt']:,}명")
with card2:
    st.metric("🍿 누적 관객수", f"{first_movie['audiAcc']:,}명")
with card3:
    st.metric("📽️ 스크린 수", f"{first_movie['scrnCnt']:,}개")
st.divider()

# 12. 순위 변동 화살표와 트로피가 들어간 표
st.subheader("🎞️ 일별 박스오피스 순위")
table_df = pd.DataFrame(
    {
        "순위": df["rank"],
        "순위 변동": df["rankInten"].apply(rank_change_label),
        "영화명": df["displayMovieNm"],
        "개봉일": df["openDt"],
        "관객수": df["audiCnt"],
        "누적관객": df["audiAcc"],
        "스크린수": df["scrnCnt"],
    }
)
styled_table = table_df.style.format(
    {"관객수": "{:,}명", "누적관객": "{:,}명", "스크린수": "{:,}개"}
).map(rank_change_style, subset=["순위 변동"])
st.dataframe(styled_table, use_container_width=True, hide_index=True)
st.caption("🔴 ↑ 순위 상승 · 🔵 ↓ 순위 하락 · 🏆 누적 관객수 100만 명 초과")
st.divider()

# 13. 관객수 상위 5편의 비교 그래프
# Plotly 그래프를 명시적으로 생성해 Streamlit의 기본 막대그래프 옵션 차이를 피합니다.
st.subheader("🍿 관객수 TOP 5 비교")
st.caption("막대가 길수록 해당 날짜에 관람한 관객이 많습니다.")
top5 = df.sort_values("audiCnt", ascending=False).head(5).copy()

if top5.empty:
    st.warning("그래프를 표시할 영화 데이터가 없습니다.")
else:
    # 가로 막대에서 가장 큰 값이 위쪽에 보이도록 작은 값부터 정렬합니다.
    chart_data = top5.sort_values("audiCnt", ascending=True).copy()
    first_rank = int(first_movie["rank"])
    bar_colors = [
        "#e50914" if int(rank) == first_rank else "#8c2733"
        for rank in chart_data["rank"]
    ]

    fig = go.Figure(
        go.Bar(
            x=chart_data["audiCnt"],
            y=chart_data["displayMovieNm"],
            orientation="h",
            marker={
                "color": bar_colors,
                "line": {"color": "#ff5964", "width": 0.7},
            },
            text=[f"{count:,}명" for count in chart_data["audiCnt"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>관객수: %{x:,}명<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(330, 72 * len(chart_data)),
        margin={"l": 10, "r": 80, "t": 20, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#f5f5f7", "size": 13},
        showlegend=False,
        xaxis={
            "title": "관객수 (명)",
            "range": [0, max(1, int(chart_data["audiCnt"].max() * 1.22))],
            "gridcolor": "rgba(255,255,255,0.12)",
            "zerolinecolor": "rgba(255,255,255,0.2)",
            "tickformat": ",",
            "ticks": "outside",
        },
        yaxis={
            "title": "",
            "showgrid": False,
            "tickfont": {"size": 13, "color": "#f5f5f7"},
            "automargin": True,
        },
        bargap=0.38,
    )

    # 이 부분에서 Plotly 그래프를 Streamlit 화면에 출력합니다.
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.caption("1위 영화는 시네마 레드로 강조했습니다.")

# 14. 데이터 출처
st.divider()
st.caption(
    "데이터 출처: 영화진흥위원회(KOBIS) "
    "영화관입장권통합전산망 일별 박스오피스 Open API"
)
