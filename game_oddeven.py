import random
import time
import numpy as np
import pandas as pd
import streamlit as st
import data_manager as dm


def init_oddeven_session_state():
    """
    홀짝 맞추기 게임 전용 세션 상태 변수를 초기화하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (내부적으로 화면 상태 저장소에 게임 전용 초기값들을 등록합니다.)
    """
    # 메인 허브가 관리하는 공용 데이터와 이름이 겹치지 않도록
    # 이 게임에서 사용하는 모든 상태 키는 반드시 'oddeven_' 접두사로 시작하게 구성합니다.
    기본_상태_목록 = {
        # 현재 선택된 게임 모드 ('🎲 운으로 맞추기' 또는 '🧠 머리로 맞추기')
        "oddeven_mode": "🎲 운으로 맞추기",
        # 현재 이어가고 있는 연승 횟수 (오답이나 시간 초과 시 0으로 초기화됨)
        "oddeven_streak": 0,
        # 현재 화면에 굴려진 주사위 눈 값들을 담는 리스트
        "oddeven_dice_list": [],
        # 머리로 맞추기 모드에서 문제가 출제된 정확한 시각(초 단위 타임스탬프)
        "oddeven_start_time": 0.0,
        # 머리로 맞추기 모드에서 현재 도전(연속 문제 출제)이 진행 중인지 여부
        "oddeven_active": False,
        # 이번 세션 동안 플레이한 모든 회차의 상세 기록을 담는 리스트
        "oddeven_history": [],
        # 직전 판정 결과를 화면에 배너와 주사위 카드로 다시 보여주기 위한 딕셔너리
        "oddeven_last_result": None,
        # 머리로 맞추기 모드에서 사용자가 설정한 제한 시간(초, 기본값 5초)
        "oddeven_time_limit": 5,
    }

    # 정의한 키들을 하나씩 확인하여 아직 세션에 존재하지 않는 항목만 기본값으로 채웁니다.
    # 이미 값이 들어 있는 경우 진행 중인 게임 데이터가 지워지지 않도록 그대로 유지합니다.
    for 상태_키, 기본값 in 기본_상태_목록.items():
        if 상태_키 not in st.session_state:
            st.session_state[상태_키] = 기본값


def roll_dice_set(dice_count, dice_sides):
    """
    지정된 개수와 면체 수에 따라 무작위 주사위 눈 리스트를 생성하는 함수입니다.

    매개변수:
        dice_count (정수): 한 번에 굴릴 주사위의 개수
        dice_sides (정수): 주사위 하나의 최대 눈 수 (면체 크기)

    반환값:
        리스트: 1부터 면체 크기 사이의 무작위 정수가 개수만큼 담긴 리스트
    """
    # 반복문 기반 리스트 내포를 사용해 지정된 개수만큼 독립적으로 주사위 눈을 추첨합니다.
    return [random.randint(1, dice_sides) for _ in range(dice_count)]


def judge_parity_and_save(
    mode_name,
    dice_list,
    user_choice,
    elapsed_time=None,
    time_limit=None,
):
    """
    주사위 눈 합계의 홀짝 여부와 사용자 선택(및 제한 시간)을 판정하고 결과를 기록하는 함수입니다.

    매개변수:
        mode_name (문자열): 플레이한 모드 이름 ('🎲 운으로 맞추기' 또는 '🧠 머리로 맞추기')
        dice_list (리스트): 이번 라운드에 나온 주사위 눈 값 목록
        user_choice (문자열): 사용자가 선택한 예측 값 ('홀수' 또는 '짝수')
        elapsed_time (실수 또는 없음): 머리로 맞추기 모드에서 문제 풀이까지 걸린 시간(초)
        time_limit (정수 또는 없음): 머리로 맞추기 모드에서 적용된 제한 시간(초)

    반환값:
        논리값: 정답(승리)이면 참, 오답이나 시간 초과(패배)이면 거짓을 반환합니다.
    """
    # 주사위 눈들의 총합을 구하고, 2로 나눈 나머지를 이용해 실제 홀짝 여부를 계산합니다.
    주사위_합계 = sum(dice_list)
    실제_홀짝 = "홀수" if 주사위_합계 % 2 != 0 else "짝수"

    # 제한 시간 초과 여부는 머리로 맞추기 모드처럼 경과 시간과 제한 시간이 전달된 경우에만 검사합니다.
    시간_초과_여부 = (
        elapsed_time is not None
        and time_limit is not None
        and elapsed_time > time_limit
    )

    # 1순위: 제한 시간을 초과한 경우, 홀짝 예측이 맞았더라도 무조건 패배로 처리합니다.
    if 시간_초과_여부:
        승리_여부 = False
        st.session_state.oddeven_streak = 0
        판정_배지 = "⏰ 시간 초과!"
        상세_메시지 = (
            f"⏰ 시간 초과! (제한 시간 {time_limit}초 / 소요 시간 {elapsed_time:.2f}초) "
            f"— 실제 합계는 {주사위_합계}({실제_홀짝})였습니다."
        )
        결과_상태 = "시간초과"

    # 2순위: 시간 내에(또는 운 모드에서) 사용자의 선택과 실제 홀짝이 일치한 경우 승리로 처리합니다.
    elif user_choice == 실제_홀짝:
        승리_여부 = True
        # 정답을 맞혔으므로 현재 연승 횟수를 1 증가시킵니다.
        st.session_state.oddeven_streak += 1
        판정_배지 = "🎉 정답!"
        if elapsed_time is not None:
            상세_메시지 = (
                f"🎉 정답! 합계 {주사위_합계}은(는) '{실제_홀짝}'입니다. "
                f"(소요 시간: {elapsed_time:.2f}초 / 현재 {st.session_state.oddeven_streak}연승)"
            )
        else:
            상세_메시지 = (
                f"🎉 정답! 합계 {주사위_합계}은(는) '{실제_홀짝}'입니다. "
                f"(현재 {st.session_state.oddeven_streak}연승)"
            )
        결과_상태 = "승리"

    # 3순위: 시간은 넘기지 않았으나 홀짝 예측이 빗나간 경우 패배로 처리합니다.
    else:
        승리_여부 = False
        # 오답이므로 현재 연승 횟수를 즉시 0으로 초기화합니다.
        st.session_state.oddeven_streak = 0
        판정_배지 = "❌ 오답!"
        if elapsed_time is not None:
            상세_메시지 = (
                f"❌ 오답! 합계 {주사위_합계}은(는) '{실제_홀짝}'입니다. "
                f"(소요 시간: {elapsed_time:.2f}초)"
            )
        else:
            상세_메시지 = f"❌ 오답! 합계 {주사위_합계}은(는) '{실제_홀짝}'입니다."
        결과_상태 = "오답"

    # 판정 결과에 따른 현재 연승 횟수를 공용 데이터 관리 모듈에 전달하여 영구 저장소에 반영합니다.
    # 연승 점수는 높을수록 좋은 기록이므로 'lower_is_better' 매개변수에 거짓을 지정합니다.
    현재_연승 = st.session_state.oddeven_streak
    dm.record_game_result(
        game_key="oddeven",
        is_win=승리_여부,
        score=현재_연승,
        lower_is_better=False,
    )

    # 화면 표에 표시할 주사위 문자열을 '[눈1, 눈2] (합계: 값)' 형식으로 만듭니다.
    주사위_표기 = f"{dice_list} (합계: {주사위_합계})"

    # 표 컴포넌트에서 숫자형과 문자형('-')이 한 열에 섞여 타입 오류가 나지 않도록
    # 화면 표시용 소요 시간은 모두 문자열로 통일하고, 통계 계산용 수치 데이터는 별도로 보관합니다.
    표시_소요시간 = f"{elapsed_time:.2f}" if elapsed_time is not None else "-"
    수치_소요시간 = float(elapsed_time) if elapsed_time is not None else None

    # 하단 대시보드에 누적될 이번 회차의 상세 기록을 세션 기록 리스트에 추가합니다.
    회차_번호 = len(st.session_state.oddeven_history) + 1
    st.session_state.oddeven_history.append(
        {
            "회차": 회차_번호,
            "선택 모드": mode_name,
            "나온 주사위 값(및 합계)": 주사위_표기,
            "내 선택": user_choice,
            "소요 시간(초)": 표시_소요시간,
            "결과": 판정_배지,
            "당시 연승 기록": 현재_연승,
            # 아래 항목들은 표에는 숨기고 하단 넘파이 통계 계산 전용으로만 사용합니다.
            "_승리여부": 승리_여부,
            "_실제홀짝": 실제_홀짝,
            "_소요시간_수치": 수치_소요시간,
        }
    )

    # 방금 끝난 라운드의 결과를 화면에 바로 출력할 수 있도록 직전 결과 상태를 저장합니다.
    st.session_state.oddeven_last_result = {
        "상태": 결과_상태,
        "배지": 판정_배지,
        "메시지": 상세_메시지,
        "주사위": dice_list,
        "합계": 주사위_합계,
        "실제_홀짝": 실제_홀짝,
        "모드": mode_name,
    }

    # 호출한 쪽에서 연속 문제 출제 여부를 결정할 수 있도록 승패 결과를 반환합니다.
    return 승리_여부


def render_cumulative_summary():
    """
    공용 데이터 저장소에서 불러온 '홀짝 맞추기'의 누적 플레이 수, 승리 수, 최고 연승 기록을 표시하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (화면 상단에 3개의 통계 지표를 가로로 나란히 출력합니다.)
    """
    # 메인 허브가 관리하는 공용 세션 데이터를 읽기 전용으로 안전하게 참조합니다.
    # 절대 공용 딕셔너리 자체를 덮어쓰거나 직접 수정하지 않습니다.
    공용_데이터 = st.session_state.get("game_data", {})
    전체_요약 = 공용_데이터.get("summary", {})
    홀짝_요약 = 전체_요약.get(
        "oddeven",
        {"played": 0, "wins": 0, "best_score": 0},
    )

    # 누적 전적과 현재 세션 연승 상태를 한눈에 파악할 수 있도록 3열 지표 카드를 배치합니다.
    열1, 열2, 열3 = st.columns(3)
    with 열1:
        st.metric(
            label="🎮 누적 플레이 수",
            value=f"{홀짝_요약.get('played', 0)}회",
        )
    with 열2:
        st.metric(
            label="🏆 누적 승리 수",
            value=f"{홀짝_요약.get('wins', 0)}회",
        )
    with 열3:
        st.metric(
            label="🔥 최고 연승 기록",
            value=f"{홀짝_요약.get('best_score', 0)}연승",
        )


def render_dice_cards(dice_list, show_sum=True):
    """
    전달받은 주사위 눈 리스트를 화면에 보기 좋은 카드 형태로 출력하는 함수입니다.

    매개변수:
        dice_list (리스트): 화면에 표시할 주사위 눈 정수 목록
        show_sum (논리값): 주사위 카드 아래에 합계를 함께 표시할지 여부

    반환값:
        없음 (주사위 개수만큼 열을 만들어 각 눈 값을 카드 UI로 출력합니다.)
    """
    # 주사위 리스트가 비어 있으면 아무것도 그리지 않고 함수를 종료합니다.
    if not dice_list:
        return

    # 주사위 개수에 맞춰 동적으로 열을 생성하여 균등한 간격으로 카드를 배치합니다.
    열_목록 = st.columns(len(dice_list))
    for 순서, 눈_값 in enumerate(dice_list, start=1):
        with 열_목록[순서 - 1]:
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align: center; font-size: 14px; color: gray;'>주사위 {순서}</div>"
                    f"<div style='text-align: center; font-size: 38px; font-weight: bold; margin: 6px 0;'>{눈_값}</div>",
                    unsafe_allow_html=True,
                )

    # 합계 공개가 허용된 상태(판정 완료 후)에만 총합과 홀짝 정보를 아래에 안내합니다.
    if show_sum:
        합계 = sum(dice_list)
        홀짝 = "홀수" if 합계 % 2 != 0 else "짝수"
        st.caption(f"🎲 나온 주사위 눈 합계: **{합계}** ({홀짝})")


def render_last_result_banner():
    """
    직전 라운드의 판정 결과(정답, 오답, 시간 초과) 배너를 화면에 출력하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (직전 결과 상태에 따라 성공, 오류, 경고 스타일의 배너를 표시합니다.)
    """
    직전_결과 = st.session_state.oddeven_last_result
    if not 직전_결과:
        return

    상태 = 직전_결과["상태"]
    메시지 = 직전_결과["메시지"]

    # 판정 결과 유형에 따라 알맞은 색상의 알림 상자를 선택해 직관적으로 결과를 전달합니다.
    if 상태 == "승리":
        st.success(메시지)
    elif 상태 == "시간초과":
        st.warning(메시지)
    else:
        st.error(메시지)


def render_luck_mode():
    """
    '🎲 운으로 맞추기' 모드의 게임 화면과 예측 우선 판정 로직을 렌더링하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (사용자가 홀수 또는 짝수 버튼을 누르면 즉시 주사위를 굴려 승패를 저장하고 화면을 갱신합니다.)
    """
    with st.container(border=True):
        st.subheader("🎲 운으로 맞추기 (예측 우선)")
        st.write(
            "주사위가 굴려지기 전에 먼저 **홀수** 또는 **짝수**를 예측해 보세요! "
            "버튼을 누르는 즉시 6면체 주사위 2개가 굴려져 승패가 결정됩니다."
        )
        st.info(f"🔥 현재 진행 중인 연승: **{st.session_state.oddeven_streak}연승**")

        # 사용자가 주사위 눈을 보기 전에 먼저 선택할 수 있도록 홀수/짝수 예측 버튼을 나란히 배치합니다.
        버튼_열1, 버튼_열2 = st.columns(2)
        with 버튼_열1:
            홀수_클릭 = st.button(
                "🔴 홀수 예측 (주사위 굴리기)",
                type="primary",
                use_container_width=True,
                key="oddeven_luck_odd_btn",
            )
        with 버튼_열2:
            짝수_클릭 = st.button(
                "🔵 짝수 예측 (주사위 굴리기)",
                type="primary",
                use_container_width=True,
                key="oddeven_luck_even_btn",
            )

        # 홀수 또는 짝수 버튼 중 하나가 클릭된 순간 주사위를 굴리고 즉시 판정합니다.
        if 홀수_클릭 or 짝수_클릭:
            사용자_선택 = "홀수" if 홀수_클릭 else "짝수"
            # 운으로 맞추기 모드에서는 1~6 눈을 가진 표준 6면체 주사위 2개를 굴립니다.
            굴린_주사위 = roll_dice_set(dice_count=2, dice_sides=6)
            st.session_state.oddeven_dice_list = 굴린_주사위

            # 운 모드는 시간 제한이 없으므로 경과 시간과 제한 시간을 비워두고 판정 함수를 호출합니다.
            judge_parity_and_save(
                mode_name="🎲 운으로 맞추기",
                dice_list=굴린_주사위,
                user_choice=사용자_선택,
                elapsed_time=None,
                time_limit=None,
            )
            # 상단 누적 전적과 하단 대시보드를 즉시 최신 상태로 반영하기 위해 화면을 새로고침합니다.
            st.rerun()

    # 직전 운 모드 판정 결과가 있다면 버튼 아래에 굴려진 주사위와 승패 배너를 이어서 보여줍니다.
    직전_결과 = st.session_state.oddeven_last_result
    if 직전_결과 and 직전_결과["모드"] == "🎲 운으로 맞추기":
        st.markdown("#### 🎯 직전 라운드 결과")
        render_dice_cards(직전_결과["주사위"], show_sum=True)
        render_last_result_banner()


def render_brain_mode():
    """
    '🧠 머리로 맞추기' 모드의 제한 시간 설정, 연속 문제 출제, 암산 후 홀짝 판정 로직을 렌더링하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (문제를 한 번 출제하면 오답이나 시간 초과로 게임이 끝날 때까지 연속으로 다음 문제를 출제합니다.)
    """
    게임_진행중 = st.session_state.oddeven_active
    직전_결과 = st.session_state.oddeven_last_result

    with st.container(border=True):
        st.subheader("🧠 머리로 맞추기 (순발력 암산 + 시간 제한)")
        st.write(
            "문제 출제 버튼을 한 번 누르면 게임이 끝나기 전까지 연속으로 문제가 나옵니다! "
            "제한 시간 안에 주사위 눈 총합의 **홀수/짝수**를 빠르게 맞혀보세요."
        )
        st.info(f"🔥 현재 진행 중인 연승: **{st.session_state.oddeven_streak}연승**")

        # 제한 시간 슬라이더는 5초~10초 범위이며, 요구사항에 따라 기본값을 반드시 5초로 설정합니다.
        # 문제가 연속 출제 중인 동안에는 공정한 진행을 위해 슬라이더 조작을 잠급니다.
        선택_제한시간 = st.slider(
            label="제한 시간(초)",
            min_value=5,
            max_value=10,
            value=5,
            disabled=게임_진행중,
            key="oddeven_brain_time_slider",
        )

        # 아직 게임이 시작되지 않았거나 직전 게임이 종료된 대기 상태일 때만 '문제 출제' 버튼을 표시합니다.
        if not 게임_진행중:
            if st.button(
                "▶️ 문제 출제 (주사위 굴리기)",
                type="primary",
                use_container_width=True,
                key="oddeven_brain_start_btn",
            ):
                # 암산의 재미를 위해 3개 또는 4개의 주사위(6면체~12면체 중 무작위)를 굴립니다.
                주사위_개수 = random.choice([3, 4])
                주사위_면체 = random.choice([6, 8, 10, 12])
                새_주사위 = roll_dice_set(주사위_개수, 주사위_면체)

                # 첫 문제의 주사위 목록, 적용된 제한 시간, 진행 플래그, 출제 시각을 세션에 저장합니다.
                st.session_state.oddeven_dice_list = 새_주사위
                st.session_state.oddeven_time_limit = 선택_제한시간
                st.session_state.oddeven_active = True
                st.session_state.oddeven_last_result = None
                st.session_state.oddeven_start_time = time.time()
                st.rerun()

        # 문제 출제 버튼으로 게임이 시작되어 연속 풀이가 진행 중일 때의 화면입니다.
        else:
            # 방금 전 문제를 맞혀서 연속 진행 중이라면 직전 정답 배너를 위에 띄워 피드백을 제공합니다.
            if 직전_결과 and 직전_결과["모드"] == "🧠 머리로 맞추기" and 직전_결과["상태"] == "승리":
                render_last_result_banner()

            st.warning(
                f"⏱️ 제한 시간 **{st.session_state.oddeven_time_limit}초** 안에 "
                "아래 주사위 눈 총합의 홀짝을 맞히세요!"
            )
            # 암산 중에는 총합 힌트를 미리 알려주지 않도록 합계 표시를 끄고 주사위 눈만 보여줍니다.
            render_dice_cards(st.session_state.oddeven_dice_list, show_sum=False)

            선택_열1, 선택_열2 = st.columns(2)
            with 선택_열1:
                홀수_응답 = st.button(
                    "🔴 홀수",
                    type="primary",
                    use_container_width=True,
                    key="oddeven_brain_odd_btn",
                )
            with 선택_열2:
                짝수_응답 = st.button(
                    "🔵 짝수",
                    type="primary",
                    use_container_width=True,
                    key="oddeven_brain_even_btn",
                )

            # 사용자가 홀수 또는 짝수 버튼을 누른 순간 경과 시간을 계산해 즉시 판정합니다.
            if 홀수_응답 or 짝수_응답:
                경과_시간 = time.time() - st.session_state.oddeven_start_time
                사용자_선택 = "홀수" if 홀수_응답 else "짝수"

                # 현재 라운드 결과를 판정하고 공용 저장소에 기록한 뒤 정답 여부를 돌려받습니다.
                정답_여부 = judge_parity_and_save(
                    mode_name="🧠 머리로 맞추기",
                    dice_list=st.session_state.oddeven_dice_list,
                    user_choice=사용자_선택,
                    elapsed_time=경과_시간,
                    time_limit=st.session_state.oddeven_time_limit,
                )

                # 정답을 맞혔다면 게임이 계속 이어지므로 즉시 새 주사위를 굴리고 타이머를 재시작합니다.
                if 정답_여부:
                    다음_주사위_개수 = random.choice([3, 4])
                    다음_주사위_면체 = random.choice([6, 8, 10, 12])
                    st.session_state.oddeven_dice_list = roll_dice_set(
                        다음_주사위_개수,
                        다음_주사위_면체,
                    )
                    st.session_state.oddeven_active = True
                    st.session_state.oddeven_start_time = time.time()
                # 오답이거나 시간 초과로 실패했다면 게임을 종료하여 다시 시작 대기 상태로 돌립니다.
                else:
                    st.session_state.oddeven_active = False

                st.rerun()

    # 오답이나 시간 초과로 게임이 끝난 직후라면 마지막 문제의 주사위 합계와 실패 배너를 아래에 보여줍니다.
    if (not 게임_진행중) and 직전_결과 and 직전_결과["모드"] == "🧠 머리로 맞추기":
        st.markdown("#### 🎯 직전 종료 라운드 결과")
        render_dice_cards(직전_결과["주사위"], show_sum=True)
        render_last_result_banner()


def render_bottom_dashboard():
    """
    화면 최하단에 이번 세션의 넘파이 통계 요약과 판다스 상세 플레이 기록표를 출력하는 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (승률, 평균 반응 속도, 홀짝 출현 비율 지표와 상세 기록 데이터프레임을 렌더링합니다.)
    """
    st.subheader("📊 이번 세션 미니 대시보드")
    기록_목록 = st.session_state.oddeven_history

    # 아직 한 판도 플레이하지 않은 초기 상태에서는 안내 문구만 표시합니다.
    if not 기록_목록:
        st.info("아직 이번 세션에서 플레이한 기록이 없습니다. 위에서 게임을 진행하면 실시간 통계와 기록표가 표시됩니다.")
        return

    # 1. 넘파이(numpy)를 활용하여 세션 통계를 정밀하게 계산합니다.
    # 각 회차의 승리 여부를 1.0(승리) 또는 0.0(패배) 배열로 변환한 뒤 평균에 100을 곱해 승률을 구합니다.
    승패_배열 = np.array(
        [1.0 if 항목["_승리여부"] else 0.0 for 항목 in 기록_목록],
        dtype=float,
    )
    세션_승률 = float(np.mean(승패_배열) * 100.0)

    # 머리로 맞추기 모드에서만 기록된 실수형 소요 시간들을 모아 평균 반응 속도를 계산합니다.
    반응_속도_목록 = [
        항목["_소요시간_수치"]
        for 항목 in 기록_목록
        if 항목["_소요시간_수치"] is not None
    ]
    if 반응_속도_목록:
        반응_속도_배열 = np.array(반응_속도_목록, dtype=float)
        평균_반응_속도_문구 = f"{float(np.mean(반응_속도_배열)):.2f}초"
    else:
        평균_반응_속도_문구 = "-"

    # 출현한 주사위의 실제 홀짝 결과를 1(홀수) 또는 0(짝수) 배열로 만들어 홀짝 출현 비율을 산출합니다.
    홀짝_배열 = np.array(
        [1.0 if 항목["_실제홀짝"] == "홀수" else 0.0 for 항목 in 기록_목록],
        dtype=float,
    )
    홀수_비율 = float(np.mean(홀짝_배열) * 100.0)
    짝수_비율 = 100.0 - 홀수_비율

    # 계산된 3가지 요약 통계를 화면에 나란히 배치합니다.
    지표_열1, 지표_열2, 지표_열3 = st.columns(3)
    with 지표_열1:
        st.metric(
            label="📈 현재 세션 승률",
            value=f"{세션_승률:.1f}%",
        )
    with 지표_열2:
        st.metric(
            label="⚡ 머리로 맞추기 평균 반응 속도",
            value=평균_반응_속도_문구,
        )
    with 지표_열3:
        st.metric(
            label="⚖️ 홀수 / 짝수 출현 비율",
            value=f"홀 {홀수_비율:.1f}% / 짝 {짝수_비율:.1f}%",
        )

    # 2. 판다스(pandas) 데이터프레임을 사용해 상세 플레이 기록표를 구성합니다.
    # 내부 통계 계산용 보조 키('_'로 시작하는 키)를 제외하고 화면 표시용 컬럼만 추출합니다.
    표시용_컬럼 = [
        "회차",
        "선택 모드",
        "나온 주사위 값(및 합계)",
        "내 선택",
        "소요 시간(초)",
        "결과",
        "당시 연승 기록",
    ]
    기록_데이터프레임 = pd.DataFrame(기록_목록)[표시용_컬럼]

    # 최신 회차가 표의 위쪽에 보이도록 회차 기준 내림차순으로 정렬하여 가독성을 높입니다.
    기록_데이터프레임 = 기록_데이터프레임.sort_values(by="회차", ascending=False)

    st.dataframe(
        기록_데이터프레임,
        use_container_width=True,
        hide_index=True,
    )


def run():
    """
    메인 허브가 동적으로 호출하는 홀짝 맞추기 게임의 유일한 진입점 함수입니다.

    매개변수:
        없음

    반환값:
        없음 (상단 누적 전적, 모드 선택, 게임 플레이 영역, 최하단 대시보드 순서로 화면을 그립니다.)
    """
    # 1. 이 게임에 필요한 전용 세션 상태 변수들을 가장 먼저 초기화합니다.
    init_oddeven_session_state()

    # 2. 게임 제목과 간단한 소개 문구를 출력합니다.
    st.title("🎲 7. 홀짝 맞추기")
    st.caption("직관으로 맞히는 '운으로 맞추기'와 빠른 암산 승부 '머리로 맞추기' 두 가지 모드를 즐겨보세요!")

    # 3. 공용 저장소에 기록된 누적 플레이 수, 승리 수, 최고 연승 기록을 상단에 실시간 표시합니다.
    render_cumulative_summary()
    st.divider()

    # 4. 상단 모드 선택 영역: 가로 라디오 버튼으로 두 가지 모드 중 하나를 고릅니다.
    모드_목록 = ["🎲 운으로 맞추기", "🧠 머리로 맞추기"]
    선택된_모드 = st.radio(
        label="플레이 모드를 선택하세요",
        options=모드_목록,
        index=모드_목록.index(st.session_state.oddeven_mode),
        horizontal=True,
        key="oddeven_mode_selector",
    )

    # 사용자가 모드를 전환한 경우, 이전 모드에서 진행 중이던 문제 상태와 직전 배너를 깔끔히 정리합니다.
    if 선택된_모드 != st.session_state.oddeven_mode:
        st.session_state.oddeven_mode = 선택된_모드
        st.session_state.oddeven_active = False
        st.session_state.oddeven_last_result = None
        st.rerun()

    # 5. 선택된 모드에 해당하는 게임 플레이 UI를 실행합니다.
    if st.session_state.oddeven_mode == "🎲 운으로 맞추기":
        render_luck_mode()
    else:
        render_brain_mode()

    # 6. 모든 게임 플레이 UI와 판정 결과가 끝난 화면 최하단에 구분선과 미니 대시보드를 배치합니다.
    st.divider()
    render_bottom_dashboard()
