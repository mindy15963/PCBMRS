import requests
import pandas as pd
from datetime import datetime

# =========================
# 사용자 설정 (반드시 수정)
# =========================
SERVICE_KEY = "decoding 키로 입력바람"  # ❗ 반드시 실제 키 넣기
EXCEL_PATH = "(25년 1분기 행정구역코드정보)dfs-zone-tree_excel.xlsx"
BASE_URL = "http://apis.data.go.kr/1360000/HealthWthrIdxServiceV3"


# =========================
# 안전한 숫자 변환
# =========================
def safe_int(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    try:
        return int(value)
    except:
        return None


# =========================
# 엑셀 로드
# =========================
def load_area_data():
    df = pd.read_excel(EXCEL_PATH)

    df["full_name"] = (
        df["1단계"].fillna("") + " " +
        df["2단계"].fillna("") + " " +
        df["3단계"].fillna("")
    )

    return df


# =========================
# 지역 검색
# =========================
def find_area_code(df, keyword):
    keyword = keyword.strip()

    # 정확 일치
    exact = df[df["full_name"] == keyword]
    if not exact.empty:
        return str(exact.iloc[0]["행정구역코드"])

    # 부분 일치
    partial = df[df["full_name"].str.contains(keyword)]
    if not partial.empty:
        return str(partial.iloc[0]["행정구역코드"])

    return None


# =========================
# 시군구 → 광역 변환
# =========================
def normalize_area_code(area_code):
    if area_code:
        return area_code[:2] + "00000000"
    return area_code


# =========================
# 시간 fallback (핵심)
# =========================
def get_base_times():
    now = datetime.now()
    today = now.strftime("%Y%m%d")

    # 최신 → 이전 순
    return [
        today + "18",
        today + "06"
    ]


# =========================
# API 호출 (완전 안정화)
# =========================
def call_api(endpoint, area_no):
    url = f"{BASE_URL}/{endpoint}"

    for base_time in get_base_times():
        params = {
            "serviceKey": SERVICE_KEY,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            "areaNo": area_no,
            "time": base_time
        }

        try:
            res = requests.get(url, params=params, timeout=5)

            print("요청 URL:", res.url)

            res.raise_for_status()
            data = res.json()

            header = data['response']['header']
            result_code = header['resultCode']

            if result_code != "00":
                print(f"[API ERROR] {endpoint} - {header['resultMsg']}")
                continue

            items = data['response']['body']['items']['item']

            if not items:
                continue

            raw = items[0].get("today")

            value = safe_int(raw)

            # ✅ 값 있으면 바로 반환
            if value is not None:
                return value

        except requests.exceptions.HTTPError as e:
            print(f"[HTTP ERROR] {endpoint}:", e)
        except Exception as e:
            print(f"[ERROR] {endpoint}:", e)

    # 모든 시도 실패
    return None


# =========================
# 꽃가루 조회
# =========================
def get_pollen_data(area_code):
    return {
        "참나무": call_api("getOakPollenRiskIdxV3", area_code),
        "소나무": call_api("getPinePollenRiskIdxV3", area_code),
        "잡초류": call_api("getWeedsPollenRiskndxV3", area_code)
    }


# =========================
# 단계 변환
# =========================
def level_to_text(value):
    return {
        0: "낮음",
        1: "보통",
        2: "높음",
        3: "매우높음"
    }.get(value, "데이터없음")


# =========================
# 마스크 판단
# =========================
def check_mask(data):
    values = [v for v in data.values() if v is not None]

    if not values:
        return "❌ 데이터 없음 (지역/시간 데이터 미제공)"

    if any(v >= 1 for v in values):
        return "😷 마스크 착용 권장"
    else:
        return "😊 마스크 불필요"


# =========================
# 실행
# =========================
if __name__ == "__main__":
    df = load_area_data()

    user_input = input("지역 입력 (예: 광주광역시 / 경기도 시흥시): ")

    # 1️⃣ 지역 코드 찾기
    area_code = find_area_code(df, user_input)

    if not area_code:
        print("❌ 지역을 찾을 수 없습니다.")
        exit()

    print(f"🔎 원본 행정구역코드: {area_code}")

    # 2️⃣ 광역 변환
    normalized_code = normalize_area_code(area_code)
    print(f"📍 조회용 행정구역코드(광역): {normalized_code}")

    # 3️⃣ 꽃가루 조회
    pollen = get_pollen_data(normalized_code)

    # 4️⃣ 출력
    print("\n🌲 꽃가루 농도")
    for k, v in pollen.items():
        print(f"{k}: {level_to_text(v)} ({v})")

    print("\n👉 결과:", check_mask(pollen))