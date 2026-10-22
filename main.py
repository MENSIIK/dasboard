# main.py
# KOBIS 공식 API를 이용해 선택한 날짜의 일별 박스오피스를 보여 주는 앱입니다.

import datetime

import pandas as pd
import requests
import streamlit as st


# 1. 페이지 기본 설정
st.set_page_config(
    page_title="박스오피스 조회",
    page_icon="🎬",
    layout="wide",
)

# 2. 한국 시간 기준으로 오늘과 어제를 계산합니다.
# 서버의 시간대와 관계없이 UTC+9(한국 표준시)를 사용합니다.
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
yesterday = today_kst - datetime.timedelta(days=1)

# 3. KOBIS 일별 박스오피스 API 주소
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

    # HTTP 상태 코드에 오류가 있으면 예외를 발생시킵니다.
    response.raise_for_status()
    return response.json()


def rank_change_label(value: int) -> str:
    """순위 변동 숫자를 화살표와 함께 표시할 문자열로 바꿉니다."""
    if value > 0:
        return f"↑ +{value}"
    if value < 0:
        return f"↓ {value}"
    return "—"


def rank_change_style(value: str) -> str:
    """순위가 오른 경우 빨간색, 내린 경우 파란색으로 표시합니다."""
    if isinstance(value, str) and value.startswith("↑"):
        return "color: #dc2626; font-weight: bold;"
    if isinstance(value, str) and value.startswith("↓"):
        return "color: #2563eb; font-weight: bold;"
    return "color: #6b7280;"


# 4. 제목과 날짜 선택기
st.title("🎬 일별 박스오피스")
st.write(
    "달력에서 날짜를 선택하면 해당 날짜의 영화 순위와 관객수를 확인할 수 있습니다."
)

# 오늘 자료는 아직 집계 전이므로 선택 가능한 마지막 날짜는 어제입니다.
selected_date = st.date_input(
    "조회 날짜 선택",
    value=yesterday,
    max_value=yesterday,
    format="YYYY-MM-DD",
)

selected_date_text = selected_date.strftime("%Y년 %m월 %d일")
target_dt = selected_date.strftime("%Y%m%d")

st.caption(f"조회 날짜: {selected_date_text} · 한국 시간 기준")
st.divider()


# 5. 비밀 금고(Secrets)에서 API 인증키를 읽습니다.
# 인증키를 소스 코드나 GitHub 저장소에 직접 적지 마세요.
try:
    api_key = str(st.secrets["KOBIS_KEY"]).strip()

    if not api_key:
        st.error("KOBIS_KEY가 비어 있습니다.")
        st.info(
            'Streamlit Cloud의 Settings → Secrets에 '
            'KOBIS_KEY = "발급받은_실제_인증키"를 등록해 주세요.'
        )
        st.stop()

except (KeyError, FileNotFoundError):
    st.error("KOBIS API 인증키를 찾을 수 없습니다.")
    st.info(
        'Streamlit Cloud의 앱 설정 → Secrets에 '
        'KOBIS_KEY = "발급받은_실제_인증키"를 등록해 주세요.'
    )
    st.stop()


# 6. API 요청 및 네트워크 오류 처리
try:
    data = fetch_boxoffice(target_dt, api_key)

except requests.exceptions.Timeout:
    st.error("KOBIS API 응답 시간이 초과되었습니다.")
    st.info("잠시 후 다시 시도하고, 네트워크와 KOBIS 서버 상태를 확인해 주세요.")
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error("KOBIS 서버에서 HTTP 오류가 발생했습니다.")
    st.caption(f"오류 정보: {e}")
    st.info("API 주소와 KOBIS 서버 상태를 확인해 주세요.")
    st.stop()

except (ValueError, requests.exceptions.JSONDecodeError):
    st.error("API 응답을 JSON으로 읽을 수 없습니다.")
    st.info("KOBIS 서버의 응답 상태를 확인한 뒤 다시 시도해 주세요.")
    st.stop()

except requests.exceptions.RequestException as e:
    st.error("KOBIS API에 연결하지 못했습니다.")
    st.caption(f"오류 정보: {e}")
    st.info("인터넷 연결, API 주소, 서버 상태를 확인해 주세요.")
    st.stop()


# 7. HTTP 200 응답이어도 faultInfo가 있으면 API 오류입니다.
if not isinstance(data, dict):
    st.error("API 응답 형식이 예상과 다릅니다.")
    st.info("KOBIS API의 응답 구조를 확인해 주세요.")
    st.stop()

if "faultInfo" in data:
    fault = data.get("faultInfo") or {}

    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "코드 없음")
        error_message = fault.get("message", "오류 메시지 없음")
    else:
        error_code = "코드 없음"
        error_message = str(fault)

    st.error("KOBIS API에서 오류 응답을 반환했습니다.")
    st.write(f"오류 코드: {error_code}")
    st.write(f"오류 메시지: {error_message}")
    st.info(
        "Secrets의 KOBIS_KEY가 정확하고 사용 가능한 인증키인지 확인해 주세요."
    )
    st.stop()


# 8. 응답 구조와 영화 목록 확인
boxoffice_result = data.get("boxOfficeResult")

if not isinstance(boxoffice_result, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.info("선택한 날짜와 KOBIS API 응답 구조를 확인해 주세요.")
    st.stop()

movie_list = boxoffice_result.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or not movie_list:
    st.warning("그날은 아직 집계 전입니다")
    st.info(
        "선택한 날짜의 자료가 아직 제공되지 않았거나 결과가 비어 있습니다. "
        "KOBIS 공식 사이트에서 해당 날짜의 일별 박스오피스를 확인해 주세요."
    )
    st.stop()


# 9. 문자열로 온 숫자 데이터를 숫자형으로 바꿉니다.
df = pd.DataFrame(movie_list)

for column in [
    "rank",
    "rankInten",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt",
]:
    if column in df.columns:
        df[column] = (
            pd.to_numeric(df[column], errors="coerce")
            .fillna(0)
            .astype(int)
        )
    else:
        # 응답에 항목이 누락되어도 앱이 중단되지 않도록 기본값을 넣습니다.
        df[column] = 0

for column in ["movieNm", "openDt"]:
    if column not in df.columns:
        df[column] = ""
    df[column] = df[column].fillna("").astype(str)


# 10. 누적 관객수가 100만 명을 초과하면 영화명에 트로피를 붙입니다.
def add_trophy(row):
    if row["audiAcc"] > 1_000_000:
        return f"🏆 {row['movieNm']}"
    return row["movieNm"]


df["displayMovieNm"] = df.apply(add_trophy, axis=1)


# 11. 1위 영화 지표 카드 3개
first_place = df[df["rank"] == 1]

if first_place.empty:
    first_movie = df.sort_values("audiCnt", ascending=False).iloc[0]
else:
    first_movie = first_place.iloc[0]

st.subheader("🏆 1위 영화")
st.markdown(f"### {first_movie['displayMovieNm']}")

card1, card2, card3 = st.columns(3)

with card1:
    st.metric("당일 관객수", f"{first_movie['audiCnt']:,}명")

with card2:
    st.metric("누적 관객수", f"{first_movie['audiAcc']:,}명")

with card3:
    st.metric("스크린 수", f"{first_movie['scrnCnt']:,}개")
