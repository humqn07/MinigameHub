import random

import numpy as np
import pandas as pd
import streamlit as st

import data_manager as dm


def init_coin_session_state():
    """
    동전 던지기 게임 전용 세션 상태 변수를 초기화하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (화면 상태 저장소에 이 게임 전용 초기값들을 안전하게 등록합니다.)
    """
    # 메인 허브가 사용하는 공용 데이터와 변수 이름이 충돌하지 않도록
    # 이 게임 전용 상태 변수는 모두 'coin_' 접두사를 붙여 관리합니다.
    기본_상태_목록 = {
        # 현재 이어가고 있는 연승 횟수 (예측 실패 시 0으로 초기화됨)
        "coin_streak": 0,
        # 이번 세션에서 동전을 던진 모든 회차의 상세 기록을 저장하는 리스트
        "coin_history": [],
        # 가장 최근에 던진 동전의 결과 요약 정보를 담는 딕셔너리 (초기에는 없음)
        "coin_last_result": None,
    }

    # 정의한 기본 키들을 하나씩 검사하여 아직 세션에 등록되지 않은 경우에만 초기값을 넣습니다.
    # 이미 값이 존재한다면 사용자가 진행 중이던 연승과 기록을 보호하기 위해 덮어쓰지 않습니다.
    for 상태_키, 기본값 in 기본_상태_목록.items():
        if 상태_키 not in st.session_state:
            st.session_state[상태_키] = 기본값


def render_cumulative_summary():
    """
    공용 데이터 저장소에서 'coin' 게임의 누적 플레이 수, 승리 수, 최고 연승 기록을 불러와 화면 상단에 표시하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (누적 전적 지표 3개를 가로 열로 나란히 출력합니다.)
    """
    # 메인 허브가 관리하는 공용 전적 데이터에서 읽기 전용으로 요약 정보를 안전하게 가져옵니다.
    # 공용 데이터 자체를 직접 수정하거나 덮어쓰는 코드는 절대 작성하지 않습니다.
    공용_데이터 = st.session_state.get("game_data", {})
    전체_요약 = 공용_데이터.get("summary", {})
    동전_요약 = 전체_요약.get(
        "coin",
        {"played": 0, "wins": 0, "best_score": 0},
    )

    # 3개의 균등한 열을 만들어 누적 플레이 수, 누적 승리 수, 최고 연승 기록을 실시간으로 보여줍니다.
    열1, 열2, 열3 = st.columns(3)
    with 열1:
        st.metric(
            label="🎮 누적 플레이 수",
            value=f"{동전_요약.get('played', 0)}회",
        )
    with 열2:
        st.metric(
            label="🏆 누적 승리 수",
            value=f"{동전_요약.get('wins', 0)}회",
        )
    with 열3:
        st.metric(
            label="🔥 최고 연승 기록",
            value=f"{동전_요약.get('best_score', 0)}연승",
        )


def toss_coin_and_record(user_choice):
    """
    동전을 무작위로 던져 승패를 판정하고, 세션 상태 갱신 및 영구 전적 저장을 수행하는 함수입니다.

    매개변수:
        user_choice (문자열): 사용자가 예측하여 선택한 동전의 면 ('앞면' 또는 '뒷면')

    반환값:
        없음 (무작위 결과 판정 후 연승 상태, 세션 기록, 공용 데이터 저장소를 모두 갱신합니다.)
    """
    # 앞면과 뒷면 중 하나를 동일한 확률(50%)로 무작위 추출하여 동전 던지기 결과를 결정합니다.
    동전_결과 = random.choice(["앞면", "뒷면"])

    # 사용자가 예측한 면과 실제로 나온 동전의 면이 같은지 비교하여 성공 여부를 판정합니다.
    성공_여부 = user_choice == 동전_결과

    # 예측에 성공했다면 현재 연승 횟수를 1 증가시키고, 실패했다면 연승을 0으로 초기화합니다.
    if 성공_여부:
        st.session_state.coin_streak += 1
        판정_문자열 = "성공"
    else:
        st.session_state.coin_streak = 0
        판정_문자열 = "실패"

    # 판정 직후 공용 데이터 관리 모듈의 기록 함수를 호출해 파일에 전적을 영구 저장합니다.
    # 동전 던지기의 연승 기록은 높을수록 좋은 점수이므로 'lower_is_better'를 거짓으로 설정합니다.
    현재_연승 = st.session_state.coin_streak
    dm.record_game_result(
        game_key="coin",
        is_win=성공_여부,
        score=현재_연승,
        lower_is_better=False,
    )

    # 이번 세션의 상세 기록 목록에 회차 번호와 투척 결과를 딕셔너리 형태로 누적합니다.
    회차_번호 = len(st.session_state.coin_history) + 1
    st.session_state.coin_history.append(
        {
            "회차": 회차_번호,
            "내 선택": user_choice,
            "동전 결과": 동전_결과,
            "판정": 판정_문자열,
            "당시 연승 기록": 현재_연승,
        }
    )

    # 화면에 직전 투척 결과를 시각적인 카드와 배너로 즉시 보여줄 수 있도록 상태에 저장합니다.
    st.session_state.coin_last_result = {
        "회차": 회차_번호,
        "내 선택": user_choice,
        "동전 결과": 동전_결과,
        "성공 여부": 성공_여부,
        "현재 연승": 현재_연승,
    }


def render_gameplay_area():
    """
    앞면/뒷면 선택 버튼과 직전 동전 투척 결과 카드 및 배너를 화면에 그리는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (버튼 클릭 시 동전을 던져 결과를 저장하고 화면을 즉시 새로고침합니다.)
    """
    # 게임 플레이 영역을 테두리 상자로 감싸 집중도를 높입니다.
    with st.container(border=True):
        st.subheader("🎯 동전 면 예측하기")
        st.info(f"🔥 현재 진행 중인 연승: **{st.session_state.coin_streak}연승**")

        # 동전을 던지기 전 사용자가 먼저 앞면 또는 뒷면을 고를 수 있게 2개의 열에 큰 버튼을 배치합니다.
        버튼_열1, 버튼_열2 = st.columns(2)
        with 버튼_열1:
            앞면_선택 = st.button(
                "🟡 앞면 (Heads)",
                type="primary",
                use_container_width=True,
                key="coin_choose_heads_btn",
            )
        with 버튼_열2:
            뒷면_선택 = st.button(
                "⚪ 뒷면 (Tails)",
                type="primary",
                use_container_width=True,
                key="coin_choose_tails_btn",
            )

        # 두 버튼 중 하나라도 클릭되면 해당 선택 값을 전달해 즉시 동전을 던지고 판정합니다.
        if 앞면_선택:
            toss_coin_and_record("앞면")
            # 상단 누적 전적과 하단 대시보드가 즉시 최신 숫자로 바뀌도록 화면을 다시 실행합니다.
            st.rerun()
        elif 뒷면_선택:
            toss_coin_and_record("뒷면")
            st.rerun()

    # 직전에 동전을 던진 기록이 존재한다면 결과 카드와 안내 배너를 명확하게 출력합니다.
    직전_결과 = st.session_state.coin_last_result
    if 직전_결과 is not None:
        실제_면 = 직전_결과["동전 결과"]
        내_선택 = 직전_결과["내 선택"]
        성공_여부 = 직전_결과["성공 여부"]
        현재_연승 = 직전_결과["현재 연승"]

        # 나온 동전 면에 맞춰 시각적 아이콘을 결정합니다.
        동전_아이콘 = "🟡" if 실제_면 == "앞면" else "⚪"

        # 직전 투척의 세부 내용을 3열 카드 형태로 깔끔하게 보여줍니다.
        with st.container(border=True):
            st.markdown(f"#### {동전_아이콘} 제 {직전_결과['회차']}회차 투척 결과")
            결과_열1, 결과_열2, 결과_열3 = st.columns(3)
            with 결과_열1:
                st.metric(label="내 선택", value=내_선택)
            with 결과_열2:
                st.metric(label="실제 나온 면", value=f"{동전_아이콘} {실제_면}")
            with 결과_열3:
                st.metric(label="현재 연승 상태", value=f"{현재_연승}연승")

        # 성공 여부에 따라 초록색 성공 배너 또는 빨간색 실패 배너를 출력합니다.
        if 성공_여부:
            st.success(
                f"🎉 예측 성공! '{실제_면}'이(가) 나왔습니다. (현재 **{현재_연승}연승** 달성 중!)"
            )
        else:
            st.error(
                f"❌ 예측 실패! 내 선택은 '{내_선택}'이었지만 실제 동전은 '{실제_면}'이(가) 나왔습니다. (연승이 0으로 초기화되었습니다.)"
            )


def render_bottom_dashboard():
    """
    화면 최하단에 이번 세션의 넘파이 통계 요약과 판다스 상세 투척 기록표를 출력하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (승률, 앞면/뒷면 출현 비율, 세션 최대 연승 지표와 상세 기록표를 화면에 그립니다.)
    """
    st.subheader("📊 이번 세션 미니 대시보드")
    기록_목록 = st.session_state.coin_history

    # 아직 이번 세션에서 동전을 한 번도 던지지 않은 경우 안내 문구만 출력하고 종료합니다.
    if not 기록_목록:
        st.info("아직 이번 세션에서 동전을 던진 기록이 없습니다. 위에서 앞면 또는 뒷면을 선택해 보세요!")
        return

    # 1. 넘파이(numpy)를 활용하여 이번 세션의 핵심 확률 및 연승 통계를 계산합니다.
    # 판정 결과를 1.0(성공)과 0.0(실패)으로 변환한 배열의 평균에 100을 곱해 세션 승률을 구합니다.
    성공_배열 = np.array(
        [1.0 if 기록["판정"] == "성공" else 0.0 for 기록 in 기록_목록],
        dtype=float,
    )
    세션_승률 = float(np.mean(성공_배열) * 100.0)

    # 동전 결과 중 '앞면'이 나온 횟수를 1.0, '뒷면'을 0.0으로 변환해 앞면 출현 비율을 구합니다.
    앞면_배열 = np.array(
        [1.0 if 기록["동전 결과"] == "앞면" else 0.0 for 기록 in 기록_목록],
        dtype=float,
    )
    앞면_출현_비율 = float(np.mean(앞면_배열) * 100.0)
    # 전체 확률 100%에서 앞면 비율을 빼서 뒷면 출현 비율을 정확히 계산합니다.
    뒷면_출현_비율 = 100.0 - 앞면_출현_비율

    # 기록된 모든 회차의 연승 숫자 중 최댓값을 넘파이 최댓값 함수로 구합니다.
    연승_배열 = np.array(
        [기록["당시 연승 기록"] for 기록 in 기록_목록],
        dtype=int,
    )
    세션_최대_연승 = int(np.max(연승_배열))

    # 계산된 4가지 요약 통계를 4개의 열에 나누어 한눈에 보기 쉽게 표시합니다.
    통계_열1, 통계_열2, 통계_열3, 통계_열4 = st.columns(4)
    with 통계_열1:
        st.metric(
            label="📈 현재 세션 승률",
            value=f"{세션_승률:.1f}%",
        )
    with 통계_열2:
        st.metric(
            label="🟡 앞면 출현 비율",
            value=f"{앞면_출현_비율:.1f}%",
        )
    with 통계_열3:
        st.metric(
            label="⚪ 뒷면 출현 비율",
            value=f"{뒷면_출현_비율:.1f}%",
        )
    with 통계_열4:
        st.metric(
            label="👑 세션 최대 연승",
            value=f"{세션_최대_연승}연승",
        )

    # 2. 판다스(pandas) 데이터프레임으로 이번 세션의 상세 투척 기록을 표로 변환합니다.
    기록_데이터프레임 = pd.DataFrame(기록_목록)

    # 가장 최근에 던진 기록이 표의 맨 위에 오도록 회차 기준 내림차순으로 정렬합니다.
    기록_데이터프레임 = 기록_데이터프레임.sort_values(by="회차", ascending=False)

    st.dataframe(
        기록_데이터프레임,
        use_container_width=True,
        hide_index=True,
    )


def run():
    """
    메인 허브가 동적으로 호출하는 동전 던지기 게임 모듈의 유일한 진입점 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (제목 및 설명, 누적 전적, 게임 플레이 영역, 최하단 대시보드를 순서대로 렌더링합니다.)
    """
    # 1. 이 게임에 필요한 전용 세션 상태 변수들을 가장 먼저 초기화합니다.
    init_coin_session_state()

    # 2. 요구된 정확한 게임 제목과 순수 운 기반 확률 게임 안내 문구를 상단에 표시합니다.
    st.title("🪙 8. 동전 던지기")
    st.caption("동전을 던져 앞면과 뒷면 중 어느 쪽이 나올지 예측해 보세요! 오직 운에 맡기는 50:50 순수 확률 게임입니다.")

    # 3. 공용 저장소에 기록된 누적 플레이 수, 승리 수, 최고 연승 기록을 상단 요약 영역에 표시합니다.
    render_cumulative_summary()
    st.divider()

    # 4. 앞면/뒷면 선택 버튼과 직전 투척 결과 배너가 포함된 게임 플레이 UI를 실행합니다.
    render_gameplay_area()

    # 5. 모든 게임 플레이 UI가 끝난 화면 최하단에 구분선을 두고 이번 세션 미니 대시보드를 배치합니다.
    st.divider()
    render_bottom_dashboard()
