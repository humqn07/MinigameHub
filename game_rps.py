import random  # 컴퓨터(AI)의 선택을 무작위로 뽑기 위한 파이썬 기본 모듈
import numpy as np  # 승률, 선택 비율 등 통계 계산을 위한 수치 계산 라이브러리
import pandas as pd  # 대결 기록을 표(데이터프레임)로 만들기 위한 라이브러리
import streamlit as st  # 웹 화면 구성을 위한 라이브러리
import data_manager as dm  # 모든 게임이 공통으로 사용하는 전적 저장 모듈

# 가위바위보에서 낼 수 있는 세 가지 선택지 목록
RPS_CHOICES = ["가위", "바위", "보"]

# 각 선택지를 화면에 보여 줄 때 함께 사용할 그림 문자
RPS_EMOJI = {"가위": "✌️", "바위": "✊", "보": "🖐️"}

# 승리 규칙표: "왼쪽(키)이 오른쪽(값)을 이긴다"는 뜻
# 예) 가위는 보를 이기고, 바위는 가위를 이기고, 보는 바위를 이긴다
RPS_WIN_RULE = {"가위": "보", "바위": "가위", "보": "바위"}


def init_rps_state():
  """
  가위바위보 모듈 전용 세션 상태 변수를 처음 한 번만 만들어 주는 함수

  - 매개변수: 없음
  - 반환값: 없음 (st.session_state 안에 값을 만들어 두기만 함)
  - 작동 방식:
    1. 화면이 다시 그려질 때마다 이 함수가 호출되지만,
       "이미 값이 있는지" 먼저 확인하므로 기존 값은 지워지지 않는다.
    2. 다른 게임 모듈과 이름이 겹치지 않도록 모든 변수 이름 앞에 rps_ 를 붙인다.
    3. 메인 시스템이 사용하는 game_data 는 "없을 때만" 파일에서 불러오며,
       이미 있으면 절대 덮어쓰지 않는다. (이 파일만 단독 점검할 때를 위한 안전장치)
  """
  # 메인 허브를 거치지 않고 실행된 경우에만 전적 데이터를 불러옴 (있으면 건드리지 않음)
  if "game_data" not in st.session_state:
    st.session_state.game_data = dm.load_data()

  # 현재 연승 횟수 (이기면 +1, 지면 0, 비기면 그대로)
  if "rps_streak" not in st.session_state:
    st.session_state.rps_streak = 0

  # 이번 접속 동안의 상세 대결 기록 목록 (한 판이 사전 한 개)
  if "rps_history" not in st.session_state:
    st.session_state.rps_history = []

  # 방금 끝난 판의 결과 (아직 한 판도 안 했으면 None)
  if "rps_last_result" not in st.session_state:
    st.session_state.rps_last_result = None


def get_computer_choice() -> str:
  """
  컴퓨터(AI)가 낼 손 모양을 무작위로 정하는 함수

  - 매개변수: 없음
  - 반환값: "가위", "바위", "보" 중 하나의 문자열
  - 작동 방식: random.choice 가 목록에서 같은 확률(각 3분의 1)로 하나를 뽑는다.
  """
  return random.choice(RPS_CHOICES)


def judge_round(player_choice: str, computer_choice: str) -> str:
  """
  내 선택과 컴퓨터의 선택을 비교해 승패를 판정하는 함수

  - 매개변수:
    player_choice: 내가 낸 손 모양 ("가위", "바위", "보" 중 하나)
    computer_choice: 컴퓨터가 낸 손 모양 ("가위", "바위", "보" 중 하나)
  - 반환값: "승리", "패배", "무승부" 중 하나의 문자열
  - 작동 방식:
    1. 두 선택이 같으면 무승부이다.
    2. 승리 규칙표에서 "내 선택이 이기는 상대"가 컴퓨터의 선택과 같으면 승리이다.
    3. 그 외의 경우는 모두 패배이다.
  """
  if player_choice == computer_choice:
    return "무승부"
  if RPS_WIN_RULE[player_choice] == computer_choice:
    return "승리"
  return "패배"


def play_round(player_choice: str):
  """
  선택 단추를 눌렀을 때 한 판을 진행하고 결과를 저장하는 함수

  - 매개변수:
    player_choice: 내가 누른 단추에 해당하는 손 모양 ("가위", "바위", "보" 중 하나)
  - 반환값: 없음 (세션 상태와 전적 파일을 갱신함)
  - 작동 방식:
    1. 컴퓨터의 선택을 무작위로 정하고 승패를 판정한다.
    2. 승리: 연승을 1 올린 뒤 dm.record_game_result 를 is_win=True 로 호출한다.
       패배: 연승을 0으로 되돌린 뒤 is_win=False, score=0 으로 호출한다.
       무승부: 전적 파일에는 아무것도 저장하지 않고 연승도 그대로 둔다.
    3. 이번 판의 내용을 rps_history 목록 끝에 추가하고,
       화면에 결과 안내를 띄울 수 있도록 rps_last_result 에도 넣어 둔다.
  - 참고: 이 함수는 단추의 on_click 으로 연결되어 "화면을 다시 그리기 전에"
    먼저 실행된다. 덕분에 화면 맨 위의 누적 전적이 누르자마자 최신 값으로 보인다.
  """
  computer_choice = get_computer_choice()  # 컴퓨터의 선택 결정
  result = judge_round(player_choice, computer_choice)  # 승패 판정

  if result == "승리":
    st.session_state.rps_streak += 1  # 연승 1 증가
    dm.record_game_result(
        game_key="rps",
        is_win=True,
        score=st.session_state.rps_streak,  # 방금 올라간 현재 연승 횟수
        lower_is_better=False,  # 연승은 높을수록 좋은 기록
    )
  elif result == "패배":
    st.session_state.rps_streak = 0  # 연승 초기화
    dm.record_game_result(
        game_key="rps",
        is_win=False,
        score=0,
        lower_is_better=False,
    )
  # 무승부일 때는 전적 저장 함수를 호출하지 않고 연승도 유지함

  # 이번 판의 상세 기록 한 줄 만들기 (표의 열 이름과 동일한 이름 사용)
  round_record = {
      "회차": len(st.session_state.rps_history) + 1,
      "내 선택": f"{RPS_EMOJI[player_choice]} {player_choice}",
      "AI 선택": f"{RPS_EMOJI[computer_choice]} {computer_choice}",
      "결과": result,
      "당시 연승": st.session_state.rps_streak,
  }
  st.session_state.rps_history.append(round_record)  # 기록 목록에 추가
  st.session_state.rps_last_result = round_record  # 방금 결과로 보관


def reset_rps_session():
  """
  이번 접속 동안 쌓인 가위바위보 기록만 지우는 함수

  - 매개변수: 없음
  - 반환값: 없음
  - 작동 방식: rps_ 로 시작하는 전용 변수(연승, 기록 목록, 방금 결과)만 처음 값으로
    되돌린다. 전적 파일에 저장된 누적 전적과 최고 연승 기록은 지워지지 않는다.
  """
  st.session_state.rps_streak = 0
  st.session_state.rps_history = []
  st.session_state.rps_last_result = None


def calc_rps_statistics(history: list) -> dict:
  """
  이번 접속 동안의 대결 기록으로 통계를 계산하는 함수 (numpy 활용)

  - 매개변수:
    history: 한 판의 기록(사전)이 순서대로 들어 있는 목록 (rps_history)
  - 반환값: 아래 항목이 들어 있는 사전
    "total": 전체 판 수
    "wins", "losses", "draws": 승리 / 패배 / 무승부 횟수
    "win_rate": 무승부를 제외한 승률(%)
    "my_counts": 내가 낸 가위/바위/보 횟수 배열
    "ai_counts": 컴퓨터가 낸 가위/바위/보 횟수 배열
    "my_ratio", "ai_ratio": 위 횟수를 비율(%)로 바꾼 배열
    "cumulative_rate": 승패가 갈린 판 기준으로 한 판씩 쌓아 가며 계산한 누적 승률(%) 배열
  - 작동 방식:
    1. 결과 열을 numpy 배열로 바꾼 뒤, "승리와 같은가?"를 비교해 참/거짓 배열을 만든다.
       참은 1, 거짓은 0으로 계산되므로 np.sum 으로 더하면 곧 횟수가 된다.
    2. 선택 열도 같은 방법으로 가위/바위/보 각각의 횟수를 센다.
    3. 누적 승률은 np.cumsum(승리를 1로 본 누적 합)을 "그때까지의 판 수"로 나누어 구한다.
  """
  # 결과와 선택을 numpy 배열로 변환 (그림 문자를 떼고 글자만 사용)
  results = np.array([row["결과"] for row in history])
  my_choices = np.array([row["내 선택"].split(" ")[-1] for row in history])
  ai_choices = np.array([row["AI 선택"].split(" ")[-1] for row in history])

  total = int(results.size)  # 전체 판 수
  wins = int(np.sum(results == "승리"))  # 승리 횟수
  losses = int(np.sum(results == "패배"))  # 패배 횟수
  draws = int(np.sum(results == "무승부"))  # 무승부 횟수

  # 승률은 승패가 갈린 판만으로 계산 (0으로 나누는 오류 방지)
  decided = wins + losses
  win_rate = float(wins / decided * 100) if decided > 0 else 0.0

  # 가위/바위/보 각각 몇 번 나왔는지 세기
  my_counts = np.array([np.sum(my_choices == c) for c in RPS_CHOICES])
  ai_counts = np.array([np.sum(ai_choices == c) for c in RPS_CHOICES])

  # 횟수를 비율(%)로 변환 (판 수가 0이면 모두 0으로 처리)
  my_ratio = my_counts / total * 100 if total > 0 else np.zeros(3)
  ai_ratio = ai_counts / total * 100 if total > 0 else np.zeros(3)

  # 무승부를 뺀 판들만 골라 누적 승률 계산
  decided_results = results[results != "무승부"]
  if decided_results.size > 0:
    win_flags = (decided_results == "승리").astype(int)  # 승리는 1, 패배는 0
    round_numbers = np.arange(1, decided_results.size + 1)  # 1, 2, 3, ... 판 번호
    cumulative_rate = np.cumsum(win_flags) / round_numbers * 100
  else:
    cumulative_rate = np.array([])

  return {
      "total": total,
      "wins": wins,
      "losses": losses,
      "draws": draws,
      "win_rate": win_rate,
      "my_counts": my_counts,
      "ai_counts": ai_counts,
      "my_ratio": my_ratio,
      "ai_ratio": ai_ratio,
      "cumulative_rate": cumulative_rate,
  }


def render_summary():
  """
  전적 파일에 저장된 가위바위보 누적 전적을 화면 위쪽에 보여 주는 함수

  - 매개변수: 없음
  - 반환값: 없음 (화면에 숫자 카드 4개를 그림)
  - 작동 방식:
    1. st.session_state.game_data["summary"]["rps"] 에서 누적 플레이 수, 승리 수,
       최고 연승 기록을 읽어 온다. (값을 읽기만 하고 고치지 않는다)
    2. 최고 연승 기록은 한 번도 이긴 적이 없으면 None 이므로 "기록 없음"으로 표시한다.
    3. 현재 연승은 이 모듈 전용 변수인 rps_streak 에서 가져온다.
  """
  summary = st.session_state.game_data["summary"]["rps"]  # 누적 전적 읽기
  played = summary["played"]
  wins = summary["wins"]
  best_score = summary["best_score"]
  best_text = f"{best_score}연승" if best_score is not None else "기록 없음"

  col_played, col_wins, col_best, col_streak = st.columns(4)
  col_played.metric("누적 플레이 수", f"{played}회")
  col_wins.metric("누적 승리 수", f"{wins}승")
  col_best.metric("최고 연승 기록", best_text)
  col_streak.metric("현재 연승", f"{st.session_state.rps_streak}연승")


def render_last_result():
  """
  방금 끝난 판의 결과를 색깔 안내 상자로 보여 주는 함수

  - 매개변수: 없음
  - 반환값: 없음
  - 작동 방식:
    1. rps_last_result 가 None 이면 아직 한 판도 하지 않은 것이므로 안내 문구만 띄운다.
    2. 승리는 초록색(st.success), 패배는 빨간색(st.error),
       무승부는 노란색(st.warning) 상자로 구분해 보여 준다.
  """
  last = st.session_state.rps_last_result
  if last is None:
    st.info("아래 단추 중 하나를 눌러 첫 판을 시작해 보세요!")
    return

  match_text = f"나: **{last['내 선택']}**  대  상대: **{last['AI 선택']}**"
  streak = last["당시 연승"]

  if last["결과"] == "승리":
    st.success(f"🎉 승리! {match_text} → 현재 **{streak}연승** 중입니다.")
  elif last["결과"] == "패배":
    st.error(f"💥 패배... {match_text} → 연승이 **0**으로 초기화되었습니다.")
  else:
    st.warning(
        f"🤝 무승부! {match_text} → 전적에는 반영되지 않으며"
        f" 현재 **{streak}연승**이 그대로 유지됩니다."
    )


def render_history_and_stats():
  """
  이번 접속의 대결 기록 표와 통계를 화면 아래쪽에 보여 주는 함수

  - 매개변수: 없음
  - 반환값: 없음
  - 작동 방식:
    1. 기록이 없으면 안내 문구만 보여 주고 끝낸다.
    2. rps_history 목록을 pandas 데이터프레임으로 바꿔 st.dataframe 으로 출력한다.
    3. calc_rps_statistics 로 계산한 승률, 승/패/무 횟수, 선택 비율을 표시하고,
       누적 승률이 어떻게 변해 왔는지 꺾은선 그래프로 그린다.
  """
  history = st.session_state.rps_history

  st.subheader("📋 이번 접속 대결 기록")
  if not history:
    st.caption("아직 대결 기록이 없습니다.")
    return

  # 열 순서를 고정해 표로 변환 (회차, 내 선택, AI 선택, 결과, 당시 연승)
  history_df = pd.DataFrame(
      history, columns=["회차", "내 선택", "AI 선택", "결과", "당시 연승"]
  )
  st.dataframe(history_df, hide_index=True)

  st.subheader("📊 이번 접속 통계")
  stats = calc_rps_statistics(history)

  col_rate, col_win, col_lose, col_draw = st.columns(4)
  col_rate.metric("승률 (무승부 제외)", f"{stats['win_rate']:.1f}%")
  col_win.metric("승리", f"{stats['wins']}회")
  col_lose.metric("패배", f"{stats['losses']}회")
  col_draw.metric("무승부", f"{stats['draws']}회")

  col_ratio, col_chart = st.columns(2)

  with col_ratio:
    st.markdown("**선택 비율 (가위 / 바위 / 보)**")
    # 나와 컴퓨터가 각각 무엇을 얼마나 냈는지 한 표로 정리
    ratio_df = pd.DataFrame({
        "선택": [f"{RPS_EMOJI[c]} {c}" for c in RPS_CHOICES],
        "내 횟수": stats["my_counts"],
        "내 비율(%)": np.round(stats["my_ratio"], 1),
        "AI 횟수": stats["ai_counts"],
        "AI 비율(%)": np.round(stats["ai_ratio"], 1),
    })
    st.dataframe(ratio_df, hide_index=True)

  with col_chart:
    st.markdown("**누적 승률 변화 (무승부 제외)**")
    if stats["cumulative_rate"].size > 0:
      # 가로축은 승패가 갈린 판의 순번, 세로축은 그 시점까지의 승률
      chart_df = pd.DataFrame(
          {"누적 승률(%)": stats["cumulative_rate"]},
          index=np.arange(1, stats["cumulative_rate"].size + 1),
      )
      st.line_chart(chart_df)
    else:
      st.caption("승패가 갈린 판이 생기면 그래프가 표시됩니다.")


def run():
  """
  가위바위보 게임 화면 전체를 그리는 진입 함수 (메인 허브에서 game_rps.run() 으로 호출)

  - 매개변수: 없음
  - 반환값: 없음
  - 작동 방식:
    1. 전용 세션 변수를 준비한다.
    2. 제목과 규칙 안내, 누적 전적 요약을 화면 위쪽에 보여 준다.
    3. 가로 3칸에 가위/바위/보 단추를 놓는다. 단추를 누르면 play_round 가 먼저
       실행되어 승패 판정과 전적 저장을 마친 뒤 화면이 다시 그려진다.
    4. 방금 결과, 대결 기록 표, 통계를 차례로 보여 준다.
  - 주의: 화면 기본 설정(st.set_page_config)은 메인 허브에서 이미 호출하므로
    이 파일에서는 호출하지 않는다.
  """
  init_rps_state()  # 전용 세션 변수 준비

  # 1. 제목과 규칙 안내
  st.title("✊ 5. 가위바위보")
  st.markdown(
      "컴퓨터와 가위바위보로 겨루는 게임입니다.\n\n"
      "- 아래 단추 중 하나를 누르면 컴퓨터도 동시에 무작위로 하나를 냅니다.\n"
      "- **승리**하면 연승이 1 올라가고, **패배**하면 연승이 0으로 돌아갑니다.\n"
      "- **무승부**는 전적에 반영되지 않으며 연승도 그대로 유지됩니다.\n"
      "- 가장 길게 이어 간 연승이 최고 기록으로 저장됩니다."
  )

  # 2. 누적 전적 요약 (전적 파일 기준)
  render_summary()
  st.divider()

  # 3. 선택 단추 3개를 가로로 배치
  st.subheader("무엇을 내시겠어요?")
  col_scissors, col_rock, col_paper = st.columns(3)
  with col_scissors:
    st.button(
        "✌️ 가위", key="rps_btn_scissors", on_click=play_round, args=("가위",)
    )
  with col_rock:
    st.button(
        "✊ 바위", key="rps_btn_rock", on_click=play_round, args=("바위",)
    )
  with col_paper:
    st.button("🖐️ 보", key="rps_btn_paper", on_click=play_round, args=("보",))

  # 4. 방금 끝난 판의 결과 안내
  render_last_result()
  st.divider()

  # 5. 대결 기록 표와 통계
  render_history_and_stats()

  # 6. 이번 접속 기록 초기화 단추 (저장된 누적 전적은 유지됨)
  if st.session_state.rps_history:
    st.button(
        "🔄 이번 접속 기록 초기화",
        key="rps_btn_reset",
        on_click=reset_rps_session,
    )
