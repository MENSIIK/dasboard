
# main.py
# 어제의 박스오피스 대시보드
# KOBIS 공식 API를 사용해 전날 영화 순위와 관객수를 보여 줍니다.

import datetime
import requests
import pandas as pd
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

# 2. 한국 시간 기준으로 어제 날짜 계산
# 서버가 어느 나라 시간대를 사용하든 한국 시간으로 계산합니다.
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
yesterday = today_kst - datetime.timedelta(days=1)

# API에 전달할 날짜는 YYYYMMDD 형식입니다.
target_dt = yesterday.strftime("%Y%m%d")

# 화면에 표시할 날짜
display_date = yesterday.strftime("%Y년 %m월 %d일")

# 3. KOBIS API 주소
API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
)

# 4. API에서 영화 목록 가져오기
@st.cache_data(ttl=1800)
def fetch_boxoffice(date_str, api_key):
    """지정한 날짜의 박스오피스 데이터를 가져옵니다."""
    response = requests.get(
        API_URL,
        params={
            "key": api_key,
            "targetDt": date_str
        },
        timeout=15
    )

    # HTTP 오류가 있으면 예외를 발생시킵니다.
    response.raise_for_status()

    # JSON 응답을 파이썬 딕셔너리로 변환합니다.
    return response.json()


# 5. 앱 제목과 조회 날짜 표시
st.title("🎬 어제의 박스오피스")
st.caption(f"조회 날짜: {display_date} · 한국 시간 기준")

st.divider()

# 6. 비밀 금고에서 인증키 가져오기
# 인증키를 코드에 직접 작성하면 안 됩니다.
try:
    api_key = st.secrets["KOBIS_KEY"]

    if not str(api_key).strip():
        st.error("KOBIS_KEY가 비어 있습니다.")
        st.info(
            "Streamlit Cloud의 앱 설정에서 Secrets를 열고 "
            "KOBIS_KEY에 발급받은 인증키를 입력해 주세요."
        )
        st.stop()

except (KeyError, FileNotFoundError):
    st.error("KOBIS API 인증키를 찾을 수 없습니다.")
    st.info(
        "Streamlit Cloud의 앱 설정 → Secrets에 "
        'KOBIS_KEY = "발급받은 인증키"를 등록해 주세요.'
    )
    st.stop()

# 7. API 요청
try:
    data = fetch_boxoffice(target_dt, str(api_key).strip())

except requests.exceptions.Timeout:
    st.error("KOBIS API 응답 시간이 초과되었습니다.")
    st.info("잠시 후 새로고침하거나 인터넷 연결 상태를 확인해 주세요.")
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error("KOBIS 서버에서 HTTP 오류가 발생했습니다.")
    st.caption(f"오류 정보: {e}")
    st.info("API 주소와 서버 상태를 확인한 뒤 다시 실행해 주세요.")
    st.stop()

except requests.exceptions.RequestException as e:
    st.error("KOBIS API에 연결하지 못했습니다.")
    st.caption(f"오류 정보: {e}")
    st.info("인터넷 연결, API 주소, 서버 상태를 확인해 주세요.")
    st.stop()

except ValueError:
    st.error("API 응답을 JSON 형식으로 읽을 수 없습니다.")
    st.info("KOBIS 서버의 응답 상태를 확인한 뒤 다시 시도해 주세요.")
    st.stop()

# 8. HTTP 200이어도 API 자체 오류인지 확인
# 인증키가 잘못된 경우 faultInfo가 반환될 수 있습니다.
if not isinstance(data, dict):
    st.error("API 응답 형식이 예상과 다릅니다.")
    st.info("KOBIS API의 응답 형식을 확인해 주세요.")
    st.stop()

if "faultInfo" in data:
    fault = data.get("faultInfo", {})
    error_code = fault.get("errorCode", "코드 없음")
    error_message = fault.get("message", "오류 메시지 없음")

    st.error("KOBIS API에서 오류 응답을 반환했습니다.")
    st.write(f"오류 코드: {error_code}")
    st.write(f"오류 메시지: {error_message}")
    st.info(
        "Secrets의 KOBIS_KEY가 올바른지, 인증키가 발급 및 "
        "사용 가능한 상태인지 확인해 주세요."
    )
    st.stop()

# 9. 응답 구조 확인
boxoffice_result = data.get("boxOfficeResult")

if not isinstance(boxoffice_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info("조회 날짜와 KOBIS API 응답 구조를 확인해 주세요.")
    st.stop()

movie_list = boxoffice_result.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning(f"{display_date}의 영화 목록이 비어 있습니다.")
    st.info(
        "해당 날짜의 집계 자료가 아직 제공되지 않았거나 "
        "API 응답에 데이터가 없을 수 있습니다. "
        "KOBIS 공식 사이트에서 해당 날짜의 일별 박스오피스를 확인해 주세요."
    )
    st.stop()

# 10. 영화 데이터를 표와 그래프에 사용할 형태로 변환
df = pd.DataFrame(movie_list)

# 숫자가 문자열로 제공되므로 정수형으로 변환합니다.
number_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]

for col in number_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    else:
        df[col] = 0

# 영화명이나 개봉일 항목이 누락된 경우에도 앱이 멈추지 않게 합니다.
for col in ["movieNm", "openDt"]:
    if col not in df.columns:
        df[col] = ""

# 11. 1위 영화 지표 카드 3개
# 순위가 1인 영화가 없으면 관객수가 가장 많은 영화를 사용합니다.
first_place = df[df["rank"] == 1]

if first_place.empty:
    first_movie = df.sort_values("audiCnt", ascending=False).iloc[0]
else:
    first_movie = first_place.iloc[0]

st.subheader("🏆 오늘의 1위 영화")
st.markdown(f"### {first_movie['movieNm']}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="당일 관객수",
        value=f"{first_movie['audiCnt']:,}명"
    )

with col2:
    st.metric(
        label="누적 관객수",
        value=f"{first_movie['audiAcc']:,}명"
    )

with col3:
    st.metric(
        label="스크린 수",
        value=f"{first_movie['scrnCnt']:,}개"
    )

st.divider()

# 12. 전체 박스오피스 표
st.subheader("📋 일별 박스오피스 순위")

# 화면에 표시할 열 이름을 한국어로 바꿉니다.
table_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].rename(
    columns={
        "rank": "순위",
        "movieNm": "영화명",
        "openDt": "개봉일",
        "audiCnt": "관객수",
        "audiAcc": "누적관객",
        "scrnCnt": "스크린수"
    }
)

# 관객수와 누적관객은 천 단위 쉼표를 표시합니다.
st.dataframe(
    table_df.style.format({
        "관객수": "{:,}명",
        "누적관객": "{:,}명",
        "스크린수": "{:,}개"
    }),
    use_container_width=True,
    hide_index=True
)

st.caption("※ 관객수는 조회 날짜 하루의 관객 수이며, 누적관객은 누적 관객 수입니다.")

st.divider()

# 13. 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5편")

top5 = df.sort_values(
    "audiCnt",
    ascending=False
).head(5).copy()

if top5.empty:
    st.warning("그래프를 표시할 영화 데이터가 없습니다.")
else:
    # 영화명을 그래프의 항목 이름으로 사용합니다.
    chart_df = top5.set_index("movieNm")[["audiCnt"]]
    chart_df = chart_df.rename(columns={"audiCnt": "관객수"})

    st.bar_chart(chart_df, horizontal=True)

    st.caption("그래프는 해당 날짜의 관객수를 기준으로 내림차순 정렬했습니다.")

# 14. 데이터 출처
st.divider()
st.caption(
    "데이터 출처: 영화진흥위원회(KOBIS) 영화관입장권통합전산망 "
    "일별 박스오피스 Open API"
)
