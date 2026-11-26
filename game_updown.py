import random  # 설정된 범위 안에서 비밀 정답 숫자를 뽑기 위한 파이썬 기본 모듈
import data_manager as dm  # 게임 종료 시 전적을 game_records.json에 저장하는 공용 모듈
import streamlit as st  # 웹 UI 구성 및 상태 관리를 위한 Streamlit 라이브러리

# 슬라이더로 조절 가능한 전체 한계 범위 (0 ~ 1000) 및 기본 시작 범위
SLIDER_LIMIT_MIN = 0
SLIDER_LIMIT_MAX = 1000
DEFAULT_MIN_NUM = 0
DEFAULT_MAX_NUM = 100
MIN_RANGE_SPAN = 10  # 최소 숫자 개수 (최소 10개 이상의 구간만 허용, 예: 0~9)


def calculate_max_attempts(min_num: int, max_num: int) -> int:
  """
  선택된 숫자 범위 크기(개수)에 맞춰 최대 입력 횟수를 유동적으로 계산하는 함수
  - 이진 탐색 기준(log2)으로 어떤 범위든 논리적으로 클리어 가능하면서 긴장감 있는 횟수 산출
  - 예: 10개(0~9) -> 4회 | 51개(0~50) -> 6회 | 101개(0~100) -> 7회 | 501개 -> 9회 | 1001개(0~1000) -> 10회
  """
  span = max(MIN_RANGE_SPAN, max_num - min_num + 1)
  return max(4, span.bit_length())


def clamp_range(sel_min: int, sel_max: int) -> tuple[int, int]:
  """사용자가 슬라이더 두 끝점을 너무 좁게 설정했을 때 최소 구간(10개)을 보장하도록 보정하는 함수"""
  if sel_max - sel_min + 1 >= MIN_RANGE_SPAN:
    return sel_min, sel_max

  # 상한선을 먼저 늘려보고, 1000에 막히면 하한선을 내림
  adjusted_max = min(SLIDER_LIMIT_MAX, sel_min + MIN_RANGE_SPAN - 1)
  adjusted_min = max(SLIDER_LIMIT_MIN, adjusted_max - MIN_RANGE_SPAN + 1)
  return adjusted_min, adjusted_max


def init_updown_state():
  """업 앤 다운 게임에 필요한 세션 상태 변수(ud_*)를 처음 한 번 초기화하는 함수"""
  if "game_data" not in st.session_state:
    st.session_state.game_data = dm.load_data()

  if "ud_min_num" not in st.session_state:
    st.session_state.ud_min_num = DEFAULT_MIN_NUM
  if "ud_max_num" not in st.session_state:
    st.session_state.ud_max_num = DEFAULT_MAX_NUM

  if "ud_max_attempts" not in st.session_state:
    st.session_state.ud_max_attempts = calculate_max_attempts(
        st.session_state.ud_min_num, st.session_state.ud_max_num
    )

  if "ud_secret" not in st.session_state:
    st.session_state.ud_secret = random.randint(
        st.session_state.ud_min_num, st.session_state.ud_max_num
    )

  if "ud_low" not in st.session_state:
    st.session_state.ud_low = st.session_state.ud_min_num
  if "ud_high" not in st.session_state:
    st.session_state.ud_high = st.session_state.ud_max_num

  if "ud_history" not in st.session_state:
    st.session_state.ud_history = []
  if "ud_last_hint" not in st.session_state:
    st.session_state.ud_last_hint = None
  if "ud_game_over" not in st.session_state:
    st.session_state.ud_game_over = False
  if "ud_is_win" not in st.session_state:
    st.session_state.ud_is_win = False


def reset_updown_game(new_min: int = None, new_max: int = None):
  """새 게임 시작 또는 슬라이더 범위 변경 시 정답·기회·추리 구간을 유동적으로 재설정하는 함수"""
  if new_min is not None and new_max is not None:
    adj_min, adj_max = clamp_range(new_min, new_max)
    st.session_state.ud_min_num = adj_min
    st.session_state.ud_max_num = adj_max

  min_num = st.session_state.ud_min_num
  max_num = st.session_state.ud_max_num

  st.session_state.ud_max_attempts = calculate_max_attempts(min_num, max_num)
  st.session_state.ud_secret = random.randint(min_num, max_num)
  st.session_state.ud_low = min_num
  st.session_state.ud_high = max_num
  st.session_state.ud_history = []
  st.session_state.ud_last_hint = None
  st.session_state.ud_game_over = False
  st.session_state.ud_is_win = False


def validate_input(user_input: str) -> tuple[bool, str]:
  """입력값이 유효한 정수이며 현재 추리 가능 구간 안에 있는지 검사하는 함수"""
  min_num = st.session_state.ud_min_num
  max_num = st.session_state.ud_max_num
  low = st.session_state.ud_low
  high = st.session_state.ud_high

  if not user_input.isdigit():
    return False, f"⚠️ {min_num}~{max_num} 사이의 정수를 정확히 입력해 주세요!"

  guess = int(user_input)
  if not (min_num <= guess <= max_num):
    return (
        False,
        f"⚠️ 설정된 전체 범위({min_num} ~ {max_num})를 벗어났습니다!",
    )

  if not (low <= guess <= high):
    return (
        False,
        f"⚠️ 이미 힌트로 좁혀진 구간({low} ~ {high}) 안의 숫자를 입력해 주세요! (기회 차감 없음)",
    )

  return True, ""


def get_proximity_tag(secret: int, guess: int, total_span: int) -> str:
  """전체 범위 크기에 비례해 정답과의 거리(온도 힌트)를 반환하는 함수"""
  diff = abs(secret - guess)
  if diff == 0:
    return "🎯 정확히 일치!"

  hot_cut = max(2, round(total_span * 0.02))
  warm_cut = max(5, round(total_span * 0.08))
  cool_cut = max(15, round(total_span * 0.25))

  if diff <= hot_cut:
    return "🔥 초근접!"
  if diff <= warm_cut:
    return "♨️ 꽤 가까움"
  if diff <= cool_cut:
    return "🌬️ 보통 거리"
  return "🧊 아주 멈"


def judge_updown(secret: int, guess: int) -> str:
  """정답(secret)과 추측값(guess)을 비교해 'UP', 'DOWN', 'CORRECT'를 반환하는 함수"""
  if guess < secret:
    return "UP"
  if guess > secret:
    return "DOWN"
  return "CORRECT"


def handle_guess(guess: int):
  """UP/DOWN 판정, 실시간 추리 구간 축소, 승패 및 JSON 전적 기록을 처리하는 함수"""
  secret = st.session_state.ud_secret
  max_attempts = st.session_state.ud_max_attempts
  total_span = st.session_state.ud_max_num - st.session_state.ud_min_num + 1

  result = judge_updown(secret, guess)
  prox_tag = get_proximity_tag(secret, guess, total_span)
  attempt_num = len(st.session_state.ud_history) + 1

  if result == "UP":
    st.session_state.ud_low = max(st.session_state.ud_low, guess + 1)
    result_text = f"🔼 UP (더 큰 숫자) · {prox_tag}"
  elif result == "DOWN":
    st.session_state.ud_high = min(st.session_state.ud_high, guess - 1)
    result_text = f"🔽 DOWN (더 작은 숫자) · {prox_tag}"
  else:
    result_text = "🎯 정답!"

  st.session_state.ud_last_hint = result_text
  st.session_state.ud_history.append({
      "시도": f"{attempt_num} / {max_attempts}회",
      "입력 숫자": guess,
      "판정 결과": result_text,
      "남은 범위": (
          "정답 확인!"
          if result == "CORRECT"
          else f"{st.session_state.ud_low} ~ {st.session_state.ud_high}"
      ),
  })

  if result == "CORRECT":
    st.session_state.ud_game_over = True
    st.session_state.ud_is_win = True
    dm.record_game_result(
        "updown", is_win=True, score=attempt_num, lower_is_better=True
    )
  elif attempt_num >= max_attempts:
    st.session_state.ud_game_over = True
    st.session_state.ud_is_win = False
    dm.record_game_result("updown", is_win=False)


def render_narrowed_range_bar():
  """설정한 전체 범위 안에서 현재 살아남은 추리 구간 [ud_low ~ ud_high]의 위치와 비율을 시각화하는 함수"""
  min_num = st.session_state.ud_min_num
  max_num = st.session_state.ud_max_num
  low = st.session_state.ud_low
  high = st.session_state.ud_high

  total_span = max(1, max_num - min_num)
  left_pct = ((low - min_num) / total_span) * 100
  width_pct = max(2.0, ((high - low) / total_span) * 100)
  candidates_left = high - low + 1
  total_candidates = max_num - min_num + 1

  st.markdown(
      f"""
      <div style="margin: 4px 0 14px 0;">
        <div style="display:flex; justify-content:space-between; font-size:0.86rem; margin-bottom:4px; opacity:0.85;">
          <span>최소 <b>{min_num}</b></span>
          <span>🔎 현재 생존 구간: <b>{low} ~ {high}</b> (후보 <b>{candidates_left}개</b> / 총 {total_candidates}개)</span>
          <span>최대 <b>{max_num}</b></span>
        </div>
        <div style="width:100%; height:14px; background:rgba(128,128,128,0.18); border-radius:7px; position:relative; overflow:hidden;">
          <div style="position:absolute; left:{left_pct:.2f}%; width:{width_pct:.2f}%; height:100%; background:linear-gradient(90deg, #3b82f6, #2563eb); border-radius:7px;"></div>
        </div>
      </div>
      """,
      unsafe_allow_html=True,
  )


def run():
  """main.py에서 카드를 클릭했을 때 호출되는 업 앤 다운 메인 실행 함수"""
  init_updown_state()

  st.header("🔢 4. 업 앤 다운")
  st.markdown(
      "**0 ~ 1000** 사이에서 원하는 숫자 범위를 바(Bar)로 자유롭게 설정해 보세요! "
      "설정한 범위 크기에 따라 **최대 입력 횟수가 유동적으로 자동 조절**됩니다."
  )

  # 1. 상단 0 ~ 1000 범위 설정 슬라이더 바 영역
  with st.container(border=True):
    col_slider, col_reset = st.columns([3.5, 1])
    with col_slider:
      sel_min, sel_max = st.slider(
          "🎚️ 추리할 숫자 범위 설정 (0 ~ 1000)",
          min_value=SLIDER_LIMIT_MIN,
          max_value=SLIDER_LIMIT_MAX,
          value=(st.session_state.ud_min_num, st.session_state.ud_max_num),
          step=1,
      )
    with col_reset:
      st.write("")
      if st.button("🔄 새 게임 시작", use_container_width=True):
        reset_updown_game()
        st.rerun()

    # 슬라이더 값이 변경되면 최소 구간(10개) 보정 후 즉시 새 범위·새 기회로 리셋
    adj_min, adj_max = clamp_range(sel_min, sel_max)
    if (
        adj_min != st.session_state.ud_min_num
        or adj_max != st.session_state.ud_max_num
    ):
      reset_updown_game(adj_min, adj_max)
      st.rerun()

  # 2. 유동적으로 계산된 입력 횟수 및 현재 범위 표시
  max_attempts = st.session_state.ud_max_attempts
  attempts_used = len(st.session_state.ud_history)
  attempts_left = max_attempts - attempts_used
  total_count = st.session_state.ud_max_num - st.session_state.ud_min_num + 1

  col_tries, col_span = st.columns(2)
  with col_tries:
    st.info(
        f"🎯 남은 입력 기회: **{attempts_left}회** / 총 **{max_attempts}회** "
        f"*(범위 {total_count}개 기준 자동 산출)*"
    )
  with col_span:
    st.info(
        f"📏 현재 추리 범위: **{st.session_state.ud_low} ~ {st.session_state.ud_high}**"
    )

  # 실시간 압축 범위 시각화 바 렌더링
  render_narrowed_range_bar()

  st.divider()

  # 3. 진행 중일 때 숫자 입력 폼 출력
  if not st.session_state.ud_game_over:
    if st.session_state.ud_last_hint:
      st.warning(f"💡 직전 판정: **{st.session_state.ud_last_hint}**")

    mid_recommend = (st.session_state.ud_low + st.session_state.ud_high) // 2
    with st.form(key="updown_form", clear_on_submit=True):
      user_input = st.text_input(
          f"숫자 입력 ({st.session_state.ud_low} ~ {st.session_state.ud_high})",
          placeholder=f"정수 입력 후 Enter (현재 중앙값: {mid_recommend})",
      )
      submitted = st.form_submit_button("확인 (제출)", use_container_width=True)

    if submitted:
      is_valid, error_msg = validate_input(user_input.strip())
      if not is_valid:
        st.error(error_msg)
      else:
        handle_guess(int(user_input.strip()))
        st.rerun()

  # 4. 게임 종료 시 승패 결과 배너 출력
  if st.session_state.ud_game_over:
    secret = st.session_state.ud_secret
    rng_str = f"{st.session_state.ud_min_num}~{st.session_state.ud_max_num}"
    if st.session_state.ud_is_win:
      st.balloons()
      st.success(
          f"🎉 정답입니다! `{rng_str}` 범위에서 **{attempts_used}번** 만에 "
          f"비밀 숫자 **{secret}**을(를) 맞혔습니다! (JSON 기록 완료)"
      )
    else:
      st.error(
          f"💥 아쉽습니다! 주어진 **{max_attempts}번**의 기회를 모두 사용했습니다. "
          f"정답은 **{secret}**이었습니다."
      )

  # 5. 시도 내역 보드 출력
  if st.session_state.ud_history:
    st.subheader("📋 추리 기록 보드")
    st.table(st.session_state.ud_history[::-1])


if __name__ == "__main__":
  run()
