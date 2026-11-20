import random  # 중복 없는 3자리 비밀 숫자를 생성하기 위한 파이썬 기본 모듈
import data_manager as dm  # 게임 종료 시 전적을 game_records.json에 저장하는 공용 모듈
import streamlit as st  # 웹 UI 구성 및 상태 관리를 위한 Streamlit 라이브러리


def init_baseball_state():
  """숫자 야구 게임에 필요한 변수(정답, 시도 기록, 게임 종료 여부)를 세션에 초기화하는 함수"""
  # 비밀 정답 숫자가 세션에 없으면 1~9 사이의 중복 없는 숫자 3개를 리스트로 뽑음 (예: [3, 8, 1])
  if "bb_secret" not in st.session_state:
    st.session_state.bb_secret = random.sample(range(1, 10), 3)

  # 사용자가 지금까지 입력한 추리 내역과 S/B 판정 결과를 담는 리스트
  if "bb_history" not in st.session_state:
    st.session_state.bb_history = []

  # 현재 판의 종료 여부 (True가 되면 입력창을 잠그고 새 게임 버튼을 강조)
  if "bb_game_over" not in st.session_state:
    st.session_state.bb_game_over = False

  # 승리 여부 (True: 3스트라이크 승리, False: 기회 소진 패배)
  if "bb_is_win" not in st.session_state:
    st.session_state.bb_is_win = False


def reset_baseball_game():
  """'새 게임 시작' 버튼을 눌렀을 때 정답과 기록을 백지상태로 초기화하는 함수"""
  st.session_state.bb_secret = random.sample(range(1, 10), 3)  # 새 정답 뽑기
  st.session_state.bb_history = []  # 이전 시도 기록 비우기
  st.session_state.bb_game_over = False  # 게임 진행 중 상태로 전환
  st.session_state.bb_is_win = False  # 승리 상태 초기화


def validate_input(user_input: str) -> tuple[bool, str]:
  """사용자가 입력한 문자열이 올바른 '중복 없는 3자리 숫자(1~9)'인지 검사하는 함수"""
  # 1. 숫자로만 이루어져 있는지, 길이가 정확히 3자리인지 검사
  if not user_input.isdigit() or len(user_input) != 3:
    return False, "⚠️ 1~9 사이의 숫자 3자리를 정확히 입력해 주세요! (예: 482)"

  # 2. 숫자 '0'이 포함되어 있는지 검사 (정답 범위가 1~9이므로 0 제외)
  if "0" in user_input:
    return False, "⚠️ 숫자 0은 사용할 수 없습니다. 1~9 사이의 숫자를 입력해 주세요!"

  # 3. set(집합)으로 변환했을 때 길이가 3이 아니면 중복된 숫자가 있다는 뜻
  if len(set(user_input)) != 3:
    return False, "⚠️ 중복되지 않는 서로 다른 숫자 3개를 입력해 주세요! (예: 123)"

  return True, ""  # 모든 검사를 통과하면 True 반환


def judge_strike_ball(secret: list, guess_str: str) -> tuple[int, int]:
  """정답 리스트(secret)와 사용자 입력(guess_str)을 비교해 스트라이크와 볼 개수를 계산하는 함수"""
  # 문자열 "482"를 정수 리스트 [4, 8, 2]로 변환
  guess = [int(ch) for ch in guess_str]

  strikes = 0  # 자리와 숫자가 모두 일치하는 개수
  balls = 0  # 숫자는 포함되지만 자리가 다른 개수

  # enumerate()를 사용해 인덱스(i)와 숫자(num)를 동시에 꺼내 비교
  for i, num in enumerate(guess):
    if num == secret[i]:  # 같은 자리에 같은 숫자가 있으면 스트라이크 +1
      strikes += 1
    elif num in secret:  # 자리는 다르지만 정답 리스트 안에 숫자가 있으면 볼 +1
      balls += 1

  return strikes, balls


def run():
  """main.py에서 메뉴를 선택했을 때 호출되는 숫자 야구 메인 실행 함수"""
  init_baseball_state()  # 1. 게임 상태 초기화 실행

  st.header("⚾ 1. 숫자 야구 게임")
  st.markdown(
      "컴퓨터가 생각한 **1~9 사이의 중복 없는 3자리 숫자**를 **최대 9번** 안에 맞혀보세요!"
  )

  # 상단 안내 및 새 게임 버튼 배치
  col_info, col_btn = st.columns([3, 1])
  with col_info:
    attempts_left = 9 - len(st.session_state.bb_history)  # 남은 기회 계산
    st.info(f"🎯 남은 기회: **{attempts_left}회** / 총 9회")
  with col_btn:
    if st.button("🔄 새 게임 시작", use_container_width=True):
      reset_baseball_game()  # 상태 초기화 후
      st.rerun()  # 화면을 즉시 새로고침

  st.divider()

  # 2. 게임이 아직 끝나지 않았을 때만 숫자 입력 폼(Form)을 보여줌
  if not st.session_state.bb_game_over:
    # st.form을 사용하면 숫자를 치고 엔터(Enter) 키만 눌러도 바로 제출됨
    with st.form(key="baseball_form", clear_on_submit=True):
      user_guess = st.text_input(
          "3자리 숫자 입력 (예: 381)", max_chars=3, placeholder="숫자 3자리 입력"
      )
      submitted = st.form_submit_button("투구하기 (제출)", use_container_width=True)

    # 제출 버튼이 눌렸을 때 처리
    if submitted:
      is_valid, error_msg = validate_input(user_guess.strip())  # 입력값 유효성 검사

      if not is_valid:
        st.error(error_msg)  # 잘못된 입력이면 경고 메시지 출력
      else:
        # 스트라이크, 볼 판정 실행
        strikes, balls = judge_strike_ball(
            st.session_state.bb_secret, user_guess.strip()
        )
        attempt_num = len(st.session_state.bb_history) + 1  # 현재 몇 번째 시도인지 계산

        # 판정 결과 문자열 만들기 (0S 0B면 OUT으로 표시)
        result_text = (
            "🚫 OUT" if (strikes == 0 and balls == 0) else f"🟡 {strikes}S {balls}B"
        )

        # 이번 시도 결과를 히스토리 리스트에 추가
        st.session_state.bb_history.append({
            "시도": f"{attempt_num}회차",
            "입력 숫자": user_guess.strip(),
            "판정 결과": result_text,
        })

        # [승리 조건] 3 스트라이크 달성 시
        if strikes == 3:
          st.session_state.bb_game_over = True
          st.session_state.bb_is_win = True
          # 공통 JSON 모듈을 호출해 승리 기록 및 시도 횟수(낮을수록 최고 기록) 저장
          dm.record_game_result(
              "baseball", is_win=True, score=attempt_num, lower_is_better=True
          )
          st.rerun()

        # [패배 조건] 9번의 기회를 모두 소진했을 시
        elif attempt_num >= 9:
          st.session_state.bb_game_over = True
          st.session_state.bb_is_win = False
          # 공통 JSON 모듈에 패배 기록 저장
          dm.record_game_result("baseball", is_win=False)
          st.rerun()

        else:
          st.rerun()  # 다음 시도를 위해 화면 갱신

  # 3. 게임이 종료되었을 때 결과 배너 출력
  if st.session_state.bb_game_over:
    answer_str = "".join(map(str, st.session_state.bb_secret))  # [3, 8, 1] -> "381" 변환
    if st.session_state.bb_is_win:
      tries = len(st.session_state.bb_history)
      st.balloons()  # 승리 축하 풍선 애니메이션
      st.success(
          f"🎉 정답입니다! **{tries}번** 만에 비밀 숫자 **{answer_str}**을(를) 맞혔습니다! (JSON 기록 완료)"
      )
    else:
      st.error(
          f"💥 아쉽습니다! 9번의 기회를 모두 사용했습니다. 정답은 **{answer_str}**이었습니다."
      )

  # 4. 지금까지 시도한 추리 기록 표(Table) 출력
  if st.session_state.bb_history:
    st.subheader("📋 추리 기록 보드")
    # 최근 시도가 맨 위에 보이도록 리스트를 역순([::-1])으로 출력
    st.table(st.session_state.bb_history[::-1])
