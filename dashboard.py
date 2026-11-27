import datetime
import platform
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import data_manager as dm


def get_game_metadata():
    """
    대시보드에서 다루는 8종 표준 게임의 고유 키와 화면 표시용 한글 이름 및 아이콘 정보를 반환하는 함수입니다.

    매개변수:
        없음

    반환값:
        딕셔너리: 각 게임 키를 키로 하고, 아이콘·한글명·차트용 짧은 이름을 값으로 가지는 사전
    """
    # 데이터 관리 모듈의 표준 게임 키 목록과 정확히 일치하도록 8종 게임의 메타 정보를 정의합니다.
    return {
        "baseball": {
            "아이콘": "⚾",
            "이름": "숫자 야구 게임",
            "표시명": "⚾ 숫자 야구 게임",
            "짧은이름": "숫자야구",
        },
        "tictactoe": {
            "아이콘": "⭕",
            "이름": "틱택토",
            "표시명": "⭕ 틱택토",
            "짧은이름": "틱택토",
        },
        "minesweeper": {
            "아이콘": "💣",
            "이름": "지뢰찾기",
            "표시명": "💣 지뢰찾기",
            "짧은이름": "지뢰찾기",
        },
        "updown": {
            "아이콘": "🔢",
            "이름": "업 앤 다운",
            "표시명": "🔢 업 앤 다운",
            "짧은이름": "업앤다운",
        },
        "rps": {
            "아이콘": "✊",
            "이름": "가위바위보",
            "표시명": "✊ 가위바위보",
            "짧은이름": "가위바위보",
        },
        "relay_math": {
            "아이콘": "➕",
            "이름": "주사위 합 연속 맞추기",
            "표시명": "➕ 주사위 합 연속 맞추기",
            "짧은이름": "주사위합",
        },
        "oddeven": {
            "아이콘": "🎲",
            "이름": "홀짝 맞추기",
            "표시명": "🎲 홀짝 맞추기",
            "짧은이름": "홀짝맞추기",
        },
        "coin": {
            "아이콘": "🪙",
            "이름": "동전 던지기",
            "표시명": "🪙 동전 던지기",
            "짧은이름": "동전던지기",
        },
    }


def init_dashboard_session_state():
    """
    대시보드 전용 임시 세션 상태 변수를 초기화하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (화면 상태 저장소에 'dash_' 접두사 변수를 안전하게 초기화합니다.)
    """
    # 메인 허브의 공용 상태와 충돌하지 않도록 대시보드 전용 상태는 'dash_' 접두사로 분리합니다.
    if "dash_last_synced" not in st.session_state:
        st.session_state.dash_last_synced = ""


def sync_latest_game_data():
    """
    데이터 관리 모듈을 통해 최신 JSON 기록 파일을 읽어와 세션 상태와 동기화하는 함수입니다.

    매개변수:
        없음

    반환값:
        딕셔너리: 파일에서 불러온 최신 플레이어 전적 및 로그 전체 데이터
    """
    # 파일 저장소에서 가장 최신 상태의 게임 전적 데이터를 불러옵니다.
    최신_데이터 = dm.load_data()

    # 다른 게임 화면과 데이터가 어긋나지 않도록 공용 세션 상태에도 최신 데이터를 동기화합니다.
    st.session_state.game_data = 최신_데이터

    # 마지막으로 데이터를 불러온 시각을 기록해 사용자가 새로고침 여부를 확인할 수 있게 합니다.
    st.session_state.dash_last_synced = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return 최신_데이터


def format_best_score(best_score):
    """
    최고 기록 수치(정수, 실수, 또는 없음)를 화면에 보기 좋은 문자열로 변환하는 함수입니다.

    매개변수:
        best_score (정수, 실수 또는 없음): 저장된 최고 기록 값

    반환값:
        문자열: 값이 없으면 '기록 없음', 정수형이면 정수 표기, 소수점이 있으면 소수 둘째 자리 표기 문자열
    """
    # 최고 기록이 0인 경우는 유효한 점수이므로, 반드시 'None' 여부로만 미기록 상태를 판별합니다.
    if best_score is None:
        return "기록 없음"

    # 실수형으로 저장되어 있더라도 소수점 이하가 0이라면 깔끔하게 정수로 변환해 보여줍니다.
    if isinstance(best_score, (int, float)):
        실수_값 = float(best_score)
        if 실수_값.is_integer():
            return f"{int(실수_값)}"
        return f"{실수_값:.2f}"

    return str(best_score)


def build_summary_records(summary_data, game_metadata):
    """
    원본 요약 딕셔너리를 순회하여 8종 게임별 통계 레코드 리스트로 정제하는 함수입니다.

    매개변수:
        summary_data (딕셔너리): JSON 파일의 'summary' 항목에 해당하는 게임별 기록 사전
        game_metadata (딕셔너리): 8종 표준 게임의 이름 및 아이콘 정보 사전

    반환값:
        리스트: 각 게임의 시도 횟수, 승리 횟수, 패배 횟수, 승률, 최고 기록이 정리된 딕셔너리 목록
    """
    # 데이터 관리 모듈에 표준 키 목록이 정의되어 있으면 그 순서를 따르고, 없으면 메타 정보 순서를 사용합니다.
    표준_키_목록 = getattr(dm, "GAME_KEYS", list(game_metadata.keys()))
    정제된_목록 = []

    for 게임_키 in 표준_키_목록:
        # 메타 정보 사전에 등록된 8종 표준 게임에 대해서만 통계를 추출합니다.
        if 게임_키 not in game_metadata:
            continue

        메타 = game_metadata[게임_키]
        게임_전적 = summary_data.get(게임_키, {})

        # 누락된 하위 키가 있더라도 오류가 나지 않도록 기본값을 안전하게 부여합니다.
        시도_횟수 = int(게임_전적.get("played", 0) or 0)
        승리_횟수 = int(게임_전적.get("wins", 0) or 0)
        패배_횟수 = max(시도_횟수 - 승리_횟수, 0)
        최고_기록 = 게임_전적.get("best_score", None)

        # 시도 횟수가 1회 이상일 때만 승률을 백분율로 계산하고, 0회면 0.0%로 처리해 0 나눗셈을 막습니다.
        if 시도_횟수 > 0:
            승률 = (승리_횟수 / 시도_횟수) * 100.0
        else:
            승률 = 0.0

        정제된_목록.append(
            {
                "게임키": 게임_키,
                "아이콘": 메타["아이콘"],
                "게임명": 메타["이름"],
                "표시명": 메타["표시명"],
                "짧은이름": 메타["짧은이름"],
                "시도 횟수": 시도_횟수,
                "승리 횟수": 승리_횟수,
                "패배 횟수": 패배_횟수,
                "승률": 승률,
                "최고 기록_원본": 최고_기록,
                "최고 기록": format_best_score(최고_기록),
            }
        )

    return 정제된_목록


def configure_matplotlib_korean_font():
    """
    운영체제에 설치된 한글 폰트를 찾아 차트 글꼴로 설정하고 성공 여부를 반환하는 함수입니다.

    매개변수:
        없음

    반환값:
        논리값: 시스템에서 한글 폰트를 찾아 적용했으면 참, 찾지 못했으면 거짓을 반환합니다.
    """
    # 차트 축에 음수 기호가 들어갈 때 글꼴 문제로 네모 상자가 출력되는 현상을 방지합니다.
    plt.rcParams["axes.unicode_minus"] = False

    # 실행 환경의 운영체제 종류에 따라 우선적으로 탐색할 한글 폰트 후보 목록을 구성합니다.
    운영체제_이름 = platform.system()
    if 운영체제_이름 == "Windows":
        한글_폰트_후보 = ["Malgun Gothic", "NanumGothic", "Gulim", "Dotum"]
    elif 운영체제_이름 == "Darwin":
        한글_폰트_후보 = ["AppleGothic", "Apple SD Gothic Neo", "NanumGothic"]
    else:
        한글_폰트_후보 = [
            "NanumGothic",
            "NanumBarunGothic",
            "Noto Sans CJK KR",
            "Noto Sans KR",
            "UnDotum",
            "Malgun Gothic",
        ]

    # 현재 환경의 폰트 관리자에 실제로 설치되어 있는 모든 폰트 이름을 집합으로 수집합니다.
    설치된_폰트_집합 = {폰트.name for 폰트 in fm.fontManager.ttflist}

    # 후보 목록을 앞에서부터 확인해 사용 가능한 첫 번째 한글 폰트를 차트 기본 글꼴로 지정합니다.
    for 폰트명 in 한글_폰트_후보:
        if 폰트명 in 설치된_폰트_집합:
            plt.rcParams["font.family"] = 폰트명
            return True

    # 설치된 한글 폰트가 전혀 없는 최소 리눅스 환경 등에서는 깨짐 방지를 위해 거짓을 반환합니다.
    return False


def render_header(player_name):
    """
    대시보드 상단 타이틀, 현재 플레이어 닉네임, 최신 기록 새로고침 버튼을 배치하는 함수입니다.

    매개변수:
        player_name (문자열): 기록 파일에 저장된 현재 플레이어의 닉네임

    반환값:
        없음 (상단 제목 영역과 새로고침 버튼 동작을 렌더링합니다.)
    """
    # 왼쪽에는 대시보드 제목과 플레이어 정보를, 오른쪽에는 새로고침 버튼을 배치하기 위해 열을 나눕니다.
    제목_열, 버튼_열 = st.columns([4, 1])

    with 제목_열:
        st.title("📊 통합 통계 대시보드")
        st.markdown(
            f"👤 현재 플레이어: **{player_name}**  |  "
            f"🕒 최근 동기화: `{st.session_state.dash_last_synced}`"
        )

    with 버튼_열:
        # 버튼이 제목과 세로 높이를 어느 정도 맞추도록 위쪽 여백을 조금 줍니다.
        st.write("")
        if st.button("🔄 최신 기록 새로고침", type="primary", use_container_width=True):
            # 버튼을 누르면 최신 JSON 데이터를 다시 불러온 뒤 화면 전체를 즉시 갱신합니다.
            sync_latest_game_data()
            st.rerun()


def render_game_cards_grid(summary_records):
    """
    8종 게임 각각의 성적을 4열 x 2행 그리드 형태의 독립된 카드 컨테이너로 출력하는 함수입니다.

    매개변수:
        summary_records (리스트): 8종 게임의 정제된 통계 딕셔너리 목록

    반환값:
        없음 (게임마다 1개의 테두리 컨테이너를 생성하여 시도 횟수, 승리 횟수, 승률, 최고 기록, 진행률 바를 표시합니다.)
    """
    st.subheader("🎮 8종 게임별 상세 성적 카드")

    # 8개 게임을 4개씩 2행으로 나누어 배치하기 위해 인덱스 0과 4를 기준으로 반복합니다.
    for 행_시작_인덱스 in range(0, len(summary_records), 4):
        행_데이터 = summary_records[행_시작_인덱스 : 행_시작_인덱스 + 4]
        카드_열_목록 = st.columns(4)

        # 한 행의 4개 열을 순회하면서 각 게임을 독립된 테두리 컨테이너 안에 그려 넣습니다.
        for 열_인덱스, 게임_정보 in enumerate(행_데이터):
            with 카드_열_목록[열_인덱스]:
                with st.container(border=True):
                    # 게임 아이콘과 한글 이름을 카드 최상단에 표시합니다.
                    st.markdown(f"#### {게임_정보['표시명']}")

                    # 시도 횟수, 승리 횟수 및 승률, 최고 기록을 읽기 쉽게 정리해 출력합니다.
                    st.write(f"**시도 횟수:** {게임_정보['시도 횟수']}회")
                    st.write(
                        f"**승리 / 승률:** {게임_정보['승리 횟수']}승 "
                        f"(`{게임_정보['승률']:.1f}%`)"
                    )
                    st.write(f"**최고 기록:** {게임_정보['최고 기록']}")

                    # 진행률 바는 0.0 이상 1.0 이하의 실수만 허용하므로 부동소수점 오차를 안전하게 제한합니다.
                    진행률_값 = min(max(게임_정보["승률"] / 100.0, 0.0), 1.0)
                    st.progress(진행률_값)


def render_overall_summary_section(summary_records, logs_data, game_metadata):
    """
    화면 최하단에 8종 게임 통합 넘파이 핵심 지표, 판다스 비교표, 막대 차트, 최근 플레이 로그를 출력하는 함수입니다.

    매개변수:
        summary_records (리스트): 8종 게임의 정제된 통계 딕셔너리 목록
        logs_data (리스트): 개별 플레이 기록 로그 리스트
        game_metadata (딕셔너리): 8종 표준 게임의 이름 및 아이콘 정보 사전

    반환값:
        없음 (종합 지표, 비교 요약표, 비교 차트, 최근 로그 표를 순서대로 렌더링합니다.)
    """
    st.subheader("🏆 전체 게임 종합 통계 요약")

    # 1. 넘파이(numpy)를 활용하여 8종 게임 전체 데이터를 통합 계산합니다.
    시도_배열 = np.array([항목["시도 횟수"] for 항목 in summary_records], dtype=int)
    승리_배열 = np.array([항목["승리 횟수"] for 항목 in summary_records], dtype=int)
    승률_배열 = np.array([항목["승률"] for 항목 in summary_records], dtype=float)

    전체_시도_합계 = int(np.sum(시도_배열))
    전체_승리_합계 = int(np.sum(승리_배열))

    # 전체 평균 승률은 전체 시도 대비 전체 승리의 비율로 계산하며, 아직 플레이가 없으면 0.0%로 둡니다.
    if 전체_시도_합계 > 0:
        전체_평균_승률 = (전체_승리_합계 / 전체_시도_합계) * 100.0

        # 최다 시도 게임은 시도 횟수 배열에서 가장 큰 값의 위치 인덱스를 찾아 이름을 가져옵니다.
        최다_시도_인덱스 = int(np.argmax(시도_배열))
        인기_게임_이름 = summary_records[최다_시도_인덱스]["표시명"]
        인기_게임_횟수 = int(시도_배열[최다_시도_인덱스])

        # 최고 승률 게임은 최소 1회 이상 플레이한 게임 중에서 승률이 가장 높은 게임을 찾습니다.
        최고_승률_인덱스 = int(np.argmax(승률_배열))
        최고_승률_게임_이름 = summary_records[최고_승률_인덱스]["표시명"]
        최고_승률_수치 = float(승률_배열[최고_승률_인덱스])

        인기_및_승률_표시 = 인기_게임_이름
        인기_및_승률_보조 = (
            f"최다 {인기_게임_횟수}회 | 최고 승률: {최고_승률_게임_이름} ({최고_승률_수치:.1f}%)"
        )
    else:
        전체_평균_승률 = 0.0
        인기_및_승률_표시 = "플레이 기록 없음"
        인기_및_승률_보조 = "게임을 1회 이상 플레이하면 집계됩니다"

    # 4개의 핵심 지표를 가로 열에 배치해 전체 현황을 한눈에 파악할 수 있게 합니다.
    지표_열1, 지표_열2, 지표_열3, 지표_열4 = st.columns(4)
    with 지표_열1:
        st.metric(
            label="🎯 전체 총 시도 횟수",
            value=f"{전체_시도_합계}회",
        )
    with 지표_열2:
        st.metric(
            label="🏅 전체 총 승리 횟수",
            value=f"{전체_승리_합계}회",
        )
    with 지표_열3:
        st.metric(
            label="📈 전체 평균 승률",
            value=f"{전체_평균_승률:.1f}%",
        )
    with 지표_열4:
        st.metric(
            label="👑 최다 시도 / 최고 승률 게임",
            value=인기_및_승률_표시,
            delta=인기_및_승률_보조,
            delta_color="off",
        )

    st.write("")

    # 2. 판다스(pandas) 데이터프레임을 이용해 8종 게임 비교 요약표를 생성합니다.
    비교_데이터 = []
    for 항목 in summary_records:
        비교_데이터.append(
            {
                "게임명": 항목["표시명"],
                "시도 횟수": 항목["시도 횟수"],
                "승리 횟수": 항목["승리 횟수"],
                "패배 횟수": 항목["패배 횟수"],
                "승률(%)": round(항목["승률"], 1),
                "최고 기록": 항목["최고 기록"],
            }
        )
    비교_데이터프레임 = pd.DataFrame(비교_데이터)

    st.markdown("#### 📋 8종 게임 비교 요약표")
    st.dataframe(
        비교_데이터프레임,
        use_container_width=True,
        hide_index=True,
    )

    # 3. 맷플롯립(matplotlib)을 활용해 게임별 시도 횟수와 승률을 나란히 비교하는 막대 차트를 그립니다.
    st.markdown("#### 📊 게임별 시도 횟수 및 승률 비교 차트")
    한글_폰트_지원 = configure_matplotlib_korean_font()

    # 한글 폰트가 정상 지원되는 환경이면 한글 축 라벨을 사용하고,
    # 폰트가 전혀 없는 환경에서는 깨진 네모 상자 출력을 막기 위해 영문 식별자 라벨로 안전하게 대체합니다.
    if 한글_폰트_지원:
        차트_게임_라벨 = [항목["짧은이름"] for 항목 in summary_records]
        제목_시도 = "게임별 시도 횟수"
        제목_승률 = "게임별 승률 (%)"
        축_시도 = "시도 횟수 (회)"
        축_승률 = "승률 (%)"
    else:
        차트_게임_라벨 = [항목["게임키"] for 항목 in summary_records]
        제목_시도 = "Played Count by Game"
        제목_승률 = "Win Rate (%) by Game"
        축_시도 = "Count"
        축_승률 = "Win Rate (%)"

    시도_값_목록 = [항목["시도 횟수"] for 항목 in summary_records]
    승률_값_목록 = [항목["승률"] for 항목 in summary_records]

    도화지, (왼쪽_축, 오른쪽_축) = plt.subplots(1, 2, figsize=(13, 4.8))

    # 왼쪽 막대 차트: 각 게임의 총 시도 횟수를 파란색 계열 막대로 표현합니다.
    막대1 = 왼쪽_축.bar(차트_게임_라벨, 시도_값_목록, color="#4C78A8", edgecolor="#2F4B7C")
    왼쪽_축.set_title(제목_시도, fontsize=12, fontweight="bold", pad=10)
    왼쪽_축.set_ylabel(축_시도)
    왼쪽_축.tick_params(axis="x", rotation=30)
    왼쪽_축.grid(axis="y", linestyle="--", alpha=0.4)
    # 막대 위쪽에 정확한 횟수 숫자를 함께 표시해 가독성을 높입니다.
    for 막대 in 막대1:
        높이 = 막대.get_height()
        왼쪽_축.text(
            막대.get_x() + 막대.get_width() / 2.0,
            높이,
            f"{int(높이)}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    # 오른쪽 막대 차트: 각 게임의 승률(0~100%)을 청록색 계열 막대로 표현합니다.
    막대2 = 오른쪽_축.bar(차트_게임_라벨, 승률_값_목록, color="#54A24B", edgecolor="#2E6B27")
    오른쪽_축.set_title(제목_승률, fontsize=12, fontweight="bold", pad=10)
    오른쪽_축.set_ylabel(축_승률)
    오른쪽_축.set_ylim(0, 110)
    오른쪽_축.tick_params(axis="x", rotation=30)
    오른쪽_축.grid(axis="y", linestyle="--", alpha=0.4)
    for 막대 in 막대2:
        높이 = 막대.get_height()
        오른쪽_축.text(
            막대.get_x() + 막대.get_width() / 2.0,
            높이,
            f"{높이:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    도화지.tight_layout()
    st.pyplot(도화지)
    # 화면 출력 후 그림 객체를 닫아 반복 새로고침 시 메모리가 불필요하게 쌓이지 않도록 정리합니다.
    plt.close(도화지)

    # 4. 최근 플레이 로그 10건을 최신순으로 정렬해 표로 보여줍니다.
    st.markdown("#### 🕒 최근 플레이 로그 (최신 10건)")
    if not logs_data:
        st.info("아직 저장된 플레이 로그가 없습니다. 미니 게임을 플레이하면 최근 기록 10건이 이곳에 표시됩니다.")
    else:
        # 로그가 저장된 순서와 타임스탬프를 함께 기준으로 삼아 가장 최근 기록이 맨 앞에 오도록 역순 정렬합니다.
        인덱스_포함_로그 = list(enumerate(logs_data))
        정렬된_로그 = sorted(
            인덱스_포함_로그,
            key=lambda 항목: (str(항목[1].get("timestamp", "")), 항목[0]),
            reverse=True,
        )
        최근_10건 = [항목[1] for 항목 in 정렬된_로그[:10]]

        로그_표_목록 = []
        for 로그 in 최근_10건:
            원본_게임키 = 로그.get("game", "")
            게임_표시명 = game_metadata.get(원본_게임키, {}).get("표시명", 원본_게임키)
            원본_결과 = 로그.get("result", "")
            결과_표시 = "🏆 승리" if 원본_결과 == "WIN" else "❌ 패배"
            점수_표시 = format_best_score(로그.get("score", None))

            로그_표_목록.append(
                {
                    "플레이 시각": 로그.get("timestamp", "-"),
                    "플레이어": 로그.get("player", "-"),
                    "게임": 게임_표시명,
                    "결과": 결과_표시,
                    "점수/기록": 점수_표시,
                }
            )

        로그_데이터프레임 = pd.DataFrame(로그_표_목록)
        st.dataframe(
            로그_데이터프레임,
            use_container_width=True,
            hide_index=True,
        )


def run():
    """
    메인 허브가 동적으로 호출하는 통합 통계 대시보드 모듈의 유일한 진입점 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (최신 데이터를 불러와 상단 헤더, 중단 8종 게임 카드, 최하단 종합 통계 순으로 출력합니다.)
    """
    # 1. 대시보드 전용 임시 세션 상태 변수를 초기화합니다.
    init_dashboard_session_state()

    # 2. 대시보드 화면이 열릴 때마다 파일에서 최신 전적 데이터를 불러와 공용 세션 상태와 동기화합니다.
    최신_데이터 = sync_latest_game_data()

    # 3. 8종 표준 게임의 메타 정보와 저장된 데이터를 결합해 통계 계산에 쓸 기본 자료를 만듭니다.
    게임_메타_정보 = get_game_metadata()
    플레이어_닉네임 = 최신_데이터.get("player_name", "플레이어")
    요약_원본 = 최신_데이터.get("summary", {})
    로그_원본 = 최신_데이터.get("logs", [])
    정제된_요약_목록 = build_summary_records(요약_원본, 게임_메타_정보)

    # 4. 상단 영역: 대시보드 제목, 플레이어 닉네임, 새로고침 버튼을 출력합니다.
    render_header(플레이어_닉네임)
    st.divider()

    # 5. 중단 영역: 8종 게임을 각각 독립된 테두리 컨테이너로 구성해 4열 x 2행 그리드로 배치합니다.
    render_game_cards_grid(정제된_요약_목록)

    # 6. 최하단 영역: 구분선 아래에 8종 게임 전체 종합 통계, 비교표, 차트, 최근 로그를 배치합니다.
    st.divider()
    render_overall_summary_section(정제된_요약_목록, 로그_원본, 게임_메타_정보)
