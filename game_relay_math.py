import random
import time

import numpy as np
import pandas as pd
import streamlit as st

import data_manager as dm


def init_dice_session_state():
    """
    주사위 합 연속 맞추기 게임 전용 세션 상태 변수를 초기화하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (내부적으로 streamlit의 세션 상태 딕셔너리에 초기값을 설정합니다.)
    """
    # 메인 허브가 관리하는 공용 전적 데이터와 충돌하지 않도록
    # 이 게임 전용 상태 변수는 모두 'dice_' 접두사를 붙여 관리합니다.
    기본_상태_목록 = {
        # 현재 도전에서 연속으로 정답을 맞힌 횟수 (초기값 0)
        "dice_streak": 0,
        # 현재 화면에 굴려져 있는 주사위 눈 값들을 담는 리스트
        "dice_values": [],
        # 현재 문제가 출제된 정확한 시각(초 단위 타임스탬프)
        "dice_start_time": 0.0,
        # 현재 게임 도전이 진행 중인지 여부를 나타내는 논리값
        "dice_playing": False,
        # 이번 도전에서 푼 문제별 상세 내역을 누적 저장하는 리스트
        "dice_history": [],
        # 도전이 한 번이라도 종료되어 결과 및 데이터 화면을 보여줘야 하는지 여부
        "dice_game_over": False,
        # 직전 제출 결과에 대한 피드백 안내 문구
        "dice_last_message": "",
        # 직전 제출 결과의 상태 구분 ('정답', '시간초과', '오답', '경고' 중 하나)
        "dice_last_status": "",
        # 사용자가 선택한 주사위 개수 (기본값 2개)
        "dice_count": 2,
        # 사용자가 선택한 주사위 면체 수 (기본값 6면체)
        "dice_sides": 6,
        # 사용자가 선택한 문제당 제한 시간(초, 기본값 10초)
        "dice_time_limit": 10,
    }

    # 정의한 기본 상태 키들을 하나씩 순회하며, 아직 세션에 없는 키만 새로 등록합니다.
    # 이미 값이 존재하는 경우에는 기존 진행 상태를 유지하기 위해 덮어쓰지 않습니다.
    for 상태_키, 기본값 in 기본_상태_목록.items():
        if 상태_키 not in st.session_state:
            st.session_state[상태_키] = 기본값


def roll_new_dice(dice_count, dice_sides):
    """
    지정된 주사위 개수와 면체 수에 맞춰 무작위 주사위 눈 목록을 생성하는 함수입니다.

    매개변수:
        dice_count (정수): 한 번에 굴릴 주사위의 개수 (2, 3, 4 중 하나)
        dice_sides (정수): 주사위 하나의 면체 수 (6, 8, 12, 20 중 하나)

    반환값:
        리스트: 1부터 면체 수 사이의 무작위 정수가 주사위 개수만큼 담긴 리스트
    """
    # 파이썬 리스트 내포 문법을 사용하여 1 이상, 면체 수 이하의 정수를
    # 주사위 개수만큼 독립적으로 무작위 추출해 반환합니다.
    return [random.randint(1, dice_sides) for _ in range(dice_count)]


def start_new_challenge(dice_count, dice_sides, time_limit):
    """
    새로운 주사위 합 연속 맞추기 도전을 시작하기 위해 게임 상태를 초기화하고 첫 주사위를 굴리는 함수입니다.

    매개변수:
        dice_count (정수): 이번 도전에서 사용할 주사위 개수
        dice_sides (정수): 이번 도전에서 사용할 주사위 면체 수
        time_limit (정수): 문제당 허용되는 제한 시간(초)

    반환값:
        없음 (세션 상태를 직접 갱신하여 즉시 게임이 시작되도록 준비합니다.)
    """
    # 사용자가 설정 창에서 고른 규칙을 세션 상태에 고정 저장합니다.
    st.session_state.dice_count = dice_count
    st.session_state.dice_sides = dice_sides
    st.session_state.dice_time_limit = time_limit

    # 새로운 도전을 시작하므로 연속 성공 횟수와 풀이 기록, 결과 메시지를 깨끗이 초기화합니다.
    st.session_state.dice_streak = 0
    st.session_state.dice_history = []
    st.session_state.dice_game_over = False
    st.session_state.dice_last_message = ""
    st.session_state.dice_last_status = ""

    # 첫 번째 라운드의 주사위를 굴리고 게임 진행 플래그를 활성화합니다.
    st.session_state.dice_values = roll_new_dice(dice_count, dice_sides)
    st.session_state.dice_playing = True

    # 첫 문제가 화면에 출제되는 기준 시각을 현재 시각으로 기록하여 정밀한 초 측정을 시작합니다.
    st.session_state.dice_start_time = time.time()


def finish_challenge_and_record(status_label, feedback_message):
    """
    오답 또는 시간 초과로 도전이 종료되었을 때 상태를 마감하고 공용 데이터 관리 모듈에 전적을 저장하는 함수입니다.

    매개변수:
        status_label (문자열): 실패 유형을 나타내는 상태 값 ('시간초과' 또는 '오답')
        feedback_message (문자열): 사용자에게 보여줄 실패 사유 안내 메시지

    반환값:
        없음 (게임 진행 상태를 종료로 바꾸고 공용 전적 저장 함수를 호출합니다.)
    """
    # 게임 진행 상태를 종료로 전환하고, 결과 요약 및 데이터 화면이 열리도록 설정합니다.
    st.session_state.dice_playing = False
    st.session_state.dice_game_over = True
    st.session_state.dice_last_status = status_label
    st.session_state.dice_last_message = feedback_message

    # 이번 도전에서 최종적으로 달성한 연속 정답 횟수를 가져옵니다.
    최종_연속_성공 = st.session_state.dice_streak

    # 규칙에 따라 1회 이상 연속 성공했으면 승리(참), 0회면 패배(거짓)로 판정합니다.
    성공_여부 = 최종_연속_성공 >= 1

    # 공용 데이터 관리 모듈의 기록 함수를 호출하여 영구 저장소에 전적을 반영합니다.
    # 연속 성공 횟수는 높을수록 좋은 점수이므로 'lower_is_better'에 거짓을 전달합니다.
    dm.record_game_result(
        game_key="relay_math",
        is_win=성공_여부,
        score=최종_연속_성공,
        lower_is_better=False,
    )


def render_cumulative_stats():
    """
    공용 세션 저장소에 기록된 '주사위 합 연속 맞추기'의 누적 전적을 화면 상단에 표시하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (화면에 누적 도전 횟수, 성공 횟수, 최고 연속 기록 지표를 출력합니다.)
    """
    # 메인 허브가 관리하는 공용 데이터에서 안전하게 요약 정보를 읽어옵니다.
    # 절대 공용 데이터를 직접 수정하거나 덮어쓰지 않고 읽기 전용으로만 접근합니다.
    공용_데이터 = st.session_state.get("game_data", {})
    요약_전체 = 공용_데이터.get("summary", {})
    게임_요약 = 요약_전체.get(
        "relay_math",
        {"played": 0, "wins": 0, "best_score": 0},
    )

    # 3개의 동일한 너비의 열을 만들어 누적 통계를 한눈에 보기 쉽게 나란히 배치합니다.
    열1, 열2, 열3 = st.columns(3)
    with 열1:
        st.metric(
            label="🎯 누적 도전 횟수",
            value=f"{게임_요약.get('played', 0)}회",
        )
    with 열2:
        st.metric(
            label="🏆 성공 횟수 (1연속 이상)",
            value=f"{게임_요약.get('wins', 0)}회",
        )
    with 열3:
        st.metric(
            label="🔥 최고 연속 정답 기록",
            value=f"{게임_요약.get('best_score', 0)}연속",
        )


def render_game_settings():
    """
    게임 시작 전(또는 도전 종료 후) 주사위 개수, 면체 수, 제한 시간을 설정하고 시작 버튼을 제공하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (사용자가 '게임 시작' 버튼을 누르면 새 도전을 시작하고 화면을 즉시 갱신합니다.)
    """
    # 설정 영역을 테두리가 있는 깔끔한 상자로 감싸 시각적으로 구분합니다.
    with st.container(border=True):
        st.subheader("⚙️ 게임 규칙 설정")

        # 주사위 면체 선택지에서 표시할 문자열과 실제 최대 눈 수를 딕셔너리로 연결합니다.
        면체_선택지 = {
            "6면체(D6)": 6,
            "8면체(D8)": 8,
            "12면체(D12)": 12,
            "20면체(D20)": 20,
        }
        # 현재 세션에 저장된 면체 수에 해당하는 기본 라벨을 찾아 초기 선택값으로 맞춥니다.
        면체_라벨_목록 = list(면체_선택지.keys())
        기본_면체_인덱스 = 0
        for 인덱스, 라벨 in enumerate(면체_라벨_목록):
            if 면체_선택지[라벨] == st.session_state.dice_sides:
                기본_면체_인덱스 = 인덱스
                break

        # 설정 항목들을 가로로 균형 있게 배치하기 위해 2개의 열로 나눕니다.
        설정_열1, 설정_열2 = st.columns(2)

        with 설정_열1:
            # 2개, 3개, 4개 중에서 굴릴 주사위 개수를 라디오 버튼으로 선택합니다.
            선택_개수 = st.radio(
                label="주사위 개수 선택",
                options=[2, 3, 4],
                index=[2, 3, 4].index(st.session_state.dice_count),
                format_func=lambda 개수: f"{개수}개",
                horizontal=True,
            )

        with 설정_열2:
            # 6면체, 8면체, 12면체, 20면체 중에서 주사위의 종류를 선택합니다.
            선택_면체_라벨 = st.selectbox(
                label="주사위 면체 선택",
                options=면체_라벨_목록,
                index=기본_면체_인덱스,
            )
            선택_면체_수 = 면체_선택지[선택_면체_라벨]

        # 5초부터 20초 사이에서 문제당 제한 시간을 슬라이더로 자유롭게 조절합니다.
        선택_제한시간 = st.slider(
            label="제한 시간(초)",
            min_value=5,
            max_value=20,
            value=st.session_state.dice_time_limit,
        )

        # 게임 시작 버튼: 누르는 즉시 타이머가 작동하며 첫 문제가 출제됩니다.
        if st.button("🎲 게임 시작", type="primary", use_container_width=True):
            start_new_challenge(선택_개수, 선택_면체_수, 선택_제한시간)
            st.rerun()


def render_active_gameplay():
    """
    진행 중인 라운드의 주사위 눈 표시, 입력 폼 렌더링, 시간 측정 및 정답 판정을 수행하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (정답이면 다음 문제를 출제하고, 오답이나 시간 초과면 도전을 종료합니다.)
    """
    # 현재 진행 중인 게임의 설정과 상태 값을 지역 변수로 불러와 가독성을 높입니다.
    현재_주사위 = st.session_state.dice_values
    현재_연속 = st.session_state.dice_streak
    제한_시간 = st.session_state.dice_time_limit
    주사위_개수 = st.session_state.dice_count
    면체_수 = st.session_state.dice_sides

    # 상단에 현재 적용된 규칙과 실시간 연속 정답 현황을 한눈에 보여줍니다.
    st.info(
        f"📌 현재 설정: **주사위 {주사위_개수}개** | **{면체_수}면체** | **제한 시간 {제한_시간}초**  "
        f"—  🔥 현재 연속 성공: **{현재_연속}회** (라운드 {현재_연속 + 1})"
    )

    # 직전 라운드에서 정답을 맞혔거나 빈 값을 입력했을 때 안내 메시지를 출력합니다.
    if st.session_state.dice_last_message:
        if st.session_state.dice_last_status == "정답":
            st.success(st.session_state.dice_last_message)
        elif st.session_state.dice_last_status == "경고":
            st.warning(st.session_state.dice_last_message)

    st.markdown("### 🎲 굴려진 주사위")

    # 굴려진 주사위 개수(2~4개)만큼 열을 동적으로 생성하여 각 눈 값을 카드 형태로 표시합니다.
    주사위_열_목록 = st.columns(len(현재_주사위))
    for 번호, 눈_값 in enumerate(현재_주사위, start=1):
        with 주사위_열_목록[번호 - 1]:
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align: center; font-size: 16px; color: gray;'>주사위 {번호}</div>"
                    f"<div style='text-align: center; font-size: 42px; font-weight: bold; margin: 8px 0;'>{눈_값}</div>",
                    unsafe_allow_html=True,
                )

    # 사용자가 숫자만 입력하고 엔터 키를 누르면 즉시 제출되도록 입력 폼을 구성합니다.
    # 매 라운드마다 폼과 입력창 키에 현재 연속 횟수를 포함시켜, 다음 문제로 넘어갈 때
    # 이전 라운드에 입력했던 숫자가 자동으로 비워지도록 설계했습니다.
    with st.form(key=f"dice_answer_form_{현재_연속}"):
        입력값 = st.number_input(
            label="주사위 눈의 합계를 입력하세요 (입력 후 엔터 키로 바로 제출)",
            min_value=0,
            max_value=주사위_개수 * 면체_수 * 2,
            value=None,
            step=1,
            placeholder="합계 숫자를 입력하세요",
            key=f"dice_number_input_{현재_연속}",
        )

        제출_여부 = st.form_submit_button(
            label="✅ 정답 제출",
            type="primary",
            use_container_width=True,
        )

    # 사용자가 제출 버튼을 누르거나 입력창에서 엔터 키를 누른 순간 실행되는 판정 로직입니다.
    if 제출_여부:
        # 문제 출제 시점부터 제출 시점까지 흐른 시간을 소수점 단위로 정밀하게 계산합니다.
        경과_시간 = time.time() - st.session_state.dice_start_time
        실제_합계 = sum(현재_주사위)
        주사위_눈_문자열 = ", ".join(str(값) for 값 in 현재_주사위)
        현재_라운드_번호 = 현재_연속 + 1

        # 먼저 제한 시간을 초과했는지 검사합니다.
        # 규칙상 제한 시간을 넘겼다면 입력값이 정답과 같더라도 시간 초과 실패로 처리합니다.
        if 경과_시간 > 제한_시간:
            표시_입력값 = str(int(입력값)) if 입력값 is not None else "미입력"
            st.session_state.dice_history.append(
                {
                    "라운드": 현재_라운드_번호,
                    "나온 주사위 눈": 주사위_눈_문자열,
                    "실제 합계": 실제_합계,
                    "내 입력값": 표시_입력값,
                    "소요 시간(초)": round(경과_시간, 2),
                    "판정 결과": "⏰ 시간 초과",
                }
            )
            실패_문구 = f"⏰ 시간 초과! (제한 시간 {제한_시간}초 / 소요 시간 {경과_시간:.2f}초)"
            finish_challenge_and_record("시간초과", 실패_문구)
            st.rerun()

        # 제한 시간 내에 제출했으나 숫자를 아무것도 입력하지 않은 경우 경고를 띄워 재입력을 유도합니다.
        elif 입력값 is None:
            st.session_state.dice_last_status = "경고"
            st.session_state.dice_last_message = "⚠️ 정답 숫자를 입력한 뒤 제출해 주세요!"
            st.rerun()

        # 제한 시간 이내에 올바른 합계를 입력한 경우: 연속 성공 횟수를 올리고 즉시 다음 문제를 출제합니다.
        elif int(입력값) == 실제_합계:
            st.session_state.dice_history.append(
                {
                    "라운드": 현재_라운드_번호,
                    "나온 주사위 눈": 주사위_눈_문자열,
                    "실제 합계": 실제_합계,
                    "내 입력값": str(int(입력값)),
                    "소요 시간(초)": round(경과_시간, 2),
                    "판정 결과": "✅ 정답",
                }
            )
            # 연속 성공 횟수를 1 증가시킵니다. (도전이 계속되므로 아직 전적 저장 함수는 호출하지 않습니다.)
            st.session_state.dice_streak += 1
            st.session_state.dice_last_status = "정답"
            st.session_state.dice_last_message = f"정답입니다! (소요 시간: {경과_시간:.2f}초)"

            # 새로운 주사위를 즉시 굴리고, 다음 라운드의 시작 시각을 현재 시각으로 초기화합니다.
            st.session_state.dice_values = roll_new_dice(주사위_개수, 면체_수)
            st.session_state.dice_start_time = time.time()
            st.rerun()

        # 제한 시간 내에 제출했지만 계산한 합계가 실제 합계와 다른 경우: 오답으로 도전을 종료합니다.
        else:
            st.session_state.dice_history.append(
                {
                    "라운드": 현재_라운드_번호,
                    "나온 주사위 눈": 주사위_눈_문자열,
                    "실제 합계": 실제_합계,
                    "내 입력값": str(int(입력값)),
                    "소요 시간(초)": round(경과_시간, 2),
                    "판정 결과": "❌ 오답",
                }
            )
            실패_문구 = f"❌ 오답입니다! (정답: {실제_합계})"
            finish_challenge_and_record("오답", 실패_문구)
            st.rerun()


def render_challenge_feedback():
    """
    도전 종료 직후 실패 사유와 최종 성공 여부 안내 배너만 간결하게 표시하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (게임 규칙 설정 UI 위에 짧은 결과 알림 문구를 렌더링합니다.)
    """
    # 종료 사유(시간 초과 또는 오답)에 따른 안내 배너를 표시해 사용자가 즉시 원인을 알 수 있게 합니다.
    st.error(st.session_state.dice_last_message)

    최종_연속 = st.session_state.dice_streak

    # 이번 도전에서 달성한 최종 연속 횟수에 따라 승리 또는 패배 기록 안내를 함께 띄웁니다.
    if 최종_연속 >= 1:
        st.success(f"🎉 도전 종료! 최종 **{최종_연속}연속 정답**을 달성하여 승리 전적으로 기록되었습니다.")
    else:
        st.warning("😢 아쉽게도 첫 라운드를 넘기지 못해 0연속으로 기록되었습니다. 다시 도전해 보세요!")


def render_challenge_data():
    """
    도전 종료 후 넘파이 기반 풀이 시간 통계와 판다스 표 형태의 상세 풀이 기록 데이터를 출력하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (게임 규칙 설정 UI 아래에 이번 도전의 통계 지표와 상세 내역 표를 렌더링합니다.)
    """
    풀이_기록 = st.session_state.dice_history
    최종_연속 = st.session_state.dice_streak

    # 기록이 1건 이상 존재하는 경우 넘파이 통계와 판다스 데이터프레임을 생성해 보여줍니다.
    if 풀이_기록:
        st.subheader("📊 이번 도전 풀이 통계 및 기록")

        기록_데이터프레임 = pd.DataFrame(풀이_기록)

        # 모든 라운드의 소요 시간을 넘파이 배열로 변환하여 평균 시간과 최단 시간을 정확히 계산합니다.
        소요_시간_배열 = np.array(기록_데이터프레임["소요 시간(초)"], dtype=float)
        평균_풀이_시간 = float(np.mean(소요_시간_배열))
        최단_풀이_시간 = float(np.min(소요_시간_배열))

        # 계산된 연속 성공 수와 넘파이 시간 통계를 3열 지표로 깔끔하게 출력합니다.
        통계_열1, 통계_열2, 통계_열3 = st.columns(3)
        with 통계_열1:
            st.metric(label="🔥 최종 연속 성공", value=f"{최종_연속}회")
        with 통계_열2:
            st.metric(label="⏱️ 평균 풀이 시간", value=f"{평균_풀이_시간:.2f}초")
        with 통계_열3:
            st.metric(label="⚡ 최단 풀이 시간", value=f"{최단_풀이_시간:.2f}초")

        # 이번 도전에서 푼 모든 문제의 상세 내역을 표로 제공합니다.
        st.dataframe(
            기록_데이터프레임,
            use_container_width=True,
            hide_index=True,
        )


def run():
    """
    메인 허브가 동적으로 호출하는 주사위 합 연속 맞추기 게임의 유일한 진입점 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (게임의 전체 UI와 상태 흐름을 순서대로 제어하여 화면을 구성합니다.)
    """
    # 1. 가장 먼저 이 게임에 필요한 세션 상태 변수들을 안전하게 초기화합니다.
    init_dice_session_state()

    # 2. 게임 제목과 간단한 규칙 설명을 화면 상단에 배치합니다.
    st.title("➕ 6. 주사위 합 연속 맞추기")
    st.caption("제한 시간 안에 굴려진 주사위 눈의 합계를 빠르고 정확하게 맞혀 연속 기록을 세워보세요!")

    # 3. 공용 저장소에 기록된 누적 도전 횟수, 성공 횟수, 최고 연속 기록을 실시간으로 표시합니다.
    render_cumulative_stats()
    st.divider()

    # 4. 현재 게임이 진행 중인지 여부에 따라 화면 구성을 알맞게 분기합니다.
    if st.session_state.dice_playing:
        # 게임 진행 중에는 주사위 눈과 정답 입력창에만 집중할 수 있도록 플레이 화면을 출력합니다.
        render_active_gameplay()
    else:
        # 도전이 방금 끝난 상태라면 먼저 간결한 실패 사유와 기록 알림만 띄워 바로 확인할 수 있게 합니다.
        if st.session_state.dice_game_over:
            render_challenge_feedback()

        # 새 도전을 바로 시작하거나 규칙을 바꿀 수 있도록 게임 규칙 설정 UI를 배치합니다.
        render_game_settings()

        # 도전 종료 후 나오는 상세 통계 및 풀이 내역 데이터 화면은 게임 규칙 설정 UI 아래에 배치합니다.
        if st.session_state.dice_game_over:
            st.divider()
            render_challenge_data()
