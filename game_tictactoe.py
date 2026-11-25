import random  # AI가 둘 빈 칸을 무작위로 선택하기 위한 파이썬 기본 모듈
import time  # 플레이어 착수 후 AI가 생각하는 자연스러운 딜레이를 주기 위한 기본 모듈
import data_manager as dm  # 게임 종료 시 전적을 game_records.json에 저장하는 공용 모듈
import streamlit as st  # 웹 UI 구성 및 상태 관리를 위한 Streamlit 라이브러리

AI_DELAY_SECONDS = 0.6  # 플레이어 착수 후 AI가 응수하기까지의 대기 시간(초)


def init_tictactoe_state():
  """틱택토 게임에 필요한 변수(보드판, 종료 여부, 승자, AI 대기 상태)를 세션에 초기화하는 함수"""
  # 3x3 격자 보드판을 길이 9의 1차원 리스트로 관리 (빈 칸은 "", 플레이어는 "O", AI는 "X")
  if "ttt_board" not in st.session_state:
    st.session_state.ttt_board = [""] * 9

  # 현재 판의 종료 여부 (True가 되면 보드판 버튼을 잠그고 결과 배너를 표시)
  if "ttt_game_over" not in st.session_state:
    st.session_state.ttt_game_over = False

  # 게임 결과 저장 (None: 진행 중, "O": 플레이어 승, "X": AI 승, "DRAW": 무승부)
  if "ttt_winner" not in st.session_state:
    st.session_state.ttt_winner = None

  # 플레이어가 둔 수(턴) 횟수를 기록하는 변수
  if "ttt_moves" not in st.session_state:
    st.session_state.ttt_moves = 0

  # AI가 딜레이를 두고 다음 수를 고민 중인지 나타내는 상태 변수
  if "ttt_ai_thinking" not in st.session_state:
    st.session_state.ttt_ai_thinking = False


def reset_tictactoe_game():
  """'새 게임 시작' 버튼을 눌렀을 때 보드판과 게임 상태를 처음 상태로 초기화하는 함수"""
  st.session_state.ttt_board = [""] * 9  # 9칸 모두 빈 칸으로 비우기
  st.session_state.ttt_game_over = False  # 게임 진행 중 상태로 전환
  st.session_state.ttt_winner = None  # 승자 정보 초기화
  st.session_state.ttt_moves = 0  # 둔 수 횟수 초기화
  st.session_state.ttt_ai_thinking = False  # AI 대기 상태 초기화


def apply_square_board_style():
  """틱택토 3x3 보드판과 각 칸의 버튼을 정사각형으로 만드는 CSS 스타일을 적용하는 함수"""
  st.markdown(
      """
      <style>
      /* 틱택토 보드 전용 컨테이너를 화면 가운데 정사각형 비율 폭으로 고정 */
      .st-key-ttt_board_box {
        max-width: 360px;
        margin: 0 auto;
      }
      /* 보드 내부의 각 칸 버튼을 가로:세로 = 1:1 정사각형으로 설정 */
      .st-key-ttt_board_box button {
        aspect-ratio: 1 / 1;
        width: 100%;
        height: auto;
        min-height: 96px;
        border-radius: 12px;
      }
      /* 칸 안의 🔵 / ❌ 아이콘을 크고 선명하게 표시 */
      .st-key-ttt_board_box button p {
        font-size: 2rem;
        font-weight: 700;
        line-height: 1;
      }
      </style>
      """,
      unsafe_allow_html=True,
  )


def check_winner(board: list):
  """3x3 보드판에서 가로·세로·대각선 8가지 승리 조건과 무승부를 판정하는 함수"""
  # 3목이 완성되는 8가지 인덱스 조합 (가로 3줄, 세로 3줄, 대각선 2줄)
  win_lines = [
      (0, 1, 2), (3, 4, 5), (6, 7, 8),  # 가로 3줄
      (0, 3, 6), (1, 4, 7), (2, 5, 8),  # 세로 3줄
      (0, 4, 8), (2, 4, 6),  # 대각선 2줄
  ]

  # 8가지 승리 조합을 하나씩 확인하여 같은 말("O" 또는 "X")이 3개 연속 놓였는지 검사
  for a, b, c in win_lines:
    if board[a] != "" and board[a] == board[b] == board[c]:
      return board[a]  # 승리한 쪽("O" 또는 "X") 반환

  # 승리자가 없는데 빈 칸("")도 더 이상 없다면 무승부 반환
  if "" not in board:
    return "DRAW"

  return None  # 아직 게임이 진행 중이면 None 반환


def get_ai_move(board: list):
  """AI("X")가 현재 보드판에서 둘 수 있는 칸의 인덱스(0~8)를 결정해 반환하는 함수"""
  # 현재 비어 있는 칸의 인덱스 목록을 리스트로 수집
  empty_cells = [i for i, cell in enumerate(board) if cell == ""]
  if not empty_cells:  # 둘 수 있는 빈 칸이 없으면 None 반환
    return None

  # 1단계(공격): AI("X")가 이번 수에 두면 바로 이길 수 있는 칸이 있는지 확인
  for idx in empty_cells:
    temp_board = board.copy()  # 원본 보드판을 건드리지 않기 위해 복사본 생성
    temp_board[idx] = "X"
    if check_winner(temp_board) == "X":
      return idx  # 즉시 승리할 수 있는 위치 반환

  # 2단계(수비): 플레이어("O")가 다음 수에 이길 수 있는 칸이 있다면 먼저 막기
  for idx in empty_cells:
    temp_board = board.copy()
    temp_board[idx] = "O"
    if check_winner(temp_board) == "O":
      return idx  # 플레이어의 3목을 막는 위치 반환

  # 3단계(무작위): 당장 이기거나 막아야 할 칸이 없으면 남은 빈 칸 중 무작위 선택
  return random.choice(empty_cells)


def handle_player_move(idx: int):
  """플레이어가 특정 칸(idx)을 클릭했을 때 착수와 승패 판정을 처리하는 함수"""
  # 이미 게임이 끝났거나, AI가 생각하는 중이거나, 이미 말이 놓인 칸이면 무시
  if (
      st.session_state.ttt_game_over
      or st.session_state.ttt_ai_thinking
      or st.session_state.ttt_board[idx] != ""
  ):
    return

  # 1. 플레이어("O") 착수 및 둔 수 횟수 +1
  st.session_state.ttt_board[idx] = "O"
  st.session_state.ttt_moves += 1

  # 2. 플레이어 착수 직후 승리 또는 무승부 판정
  result = check_winner(st.session_state.ttt_board)
  if result == "O":
    st.session_state.ttt_game_over = True
    st.session_state.ttt_winner = "O"
    # 공통 JSON 모듈에 승리 기록 및 최소 착수 횟수(낮을수록 최고 기록) 저장
    dm.record_game_result(
        "tictactoe",
        is_win=True,
        score=st.session_state.ttt_moves,
        lower_is_better=True,
    )
  elif result == "DRAW":
    st.session_state.ttt_game_over = True
    st.session_state.ttt_winner = "DRAW"
    # 무승부는 승리가 아니므로 is_win=False로 전적 기록
    dm.record_game_result("tictactoe", is_win=False)
  else:
    # 게임이 끝나지 않았으면 먼저 화면에 플레이어 말을 보여준 뒤 AI 차례로 전환
    st.session_state.ttt_ai_thinking = True


def handle_ai_move():
  """딜레이 후 AI("X")가 수를 두고 승패 또는 무승부를 판정하는 함수"""
  ai_idx = get_ai_move(st.session_state.ttt_board)  # AI가 둘 칸 인덱스 계산
  if ai_idx is not None:
    st.session_state.ttt_board[ai_idx] = "X"  # 보드판에 AI 말 착수

  # AI 착수 직후 AI 승리 또는 무승부 판정
  result = check_winner(st.session_state.ttt_board)
  if result == "X":
    st.session_state.ttt_game_over = True
    st.session_state.ttt_winner = "X"
    # AI 승리 시 플레이어 패배 기록 저장
    dm.record_game_result("tictactoe", is_win=False)
  elif result == "DRAW":
    st.session_state.ttt_game_over = True
    st.session_state.ttt_winner = "DRAW"
    dm.record_game_result("tictactoe", is_win=False)

  st.session_state.ttt_ai_thinking = False  # AI 차례 종료


def run():
  """main.py에서 메뉴를 선택했을 때 호출되는 틱택토 메인 실행 함수"""
  init_tictactoe_state()  # 1. 게임 상태 초기화 실행
  apply_square_board_style()  # 2. 정사각형 보드판 CSS 스타일 적용

  st.header("⭕ 2. 틱택토")
  st.markdown(
      "3×3 정사각형 보드판에서 가로·세로·대각선 **3목**을 먼저 완성해 보세요!"
  )

  # 플레이어(🔵)와 AI(❌) 구분을 명확하게 보여주는 상단 범례
  col_player, col_ai = st.columns(2)
  with col_player:
    st.info("👤 **플레이어 (나): 🔵 파란 동그라미**")
  with col_ai:
    st.error("🤖 **AI (컴퓨터): ❌ 빨간 엑스**")

  # 현재 차례 안내 및 새 게임 버튼 배치 (game_baseball.py와 동일한 3:1 비율)
  col_info, col_btn = st.columns([3, 1])
  with col_info:
    if st.session_state.ttt_game_over:
      st.info("🏁 게임이 종료되었습니다. 새 게임을 시작해 보세요!")
    elif st.session_state.ttt_ai_thinking:
      st.warning("🤖 AI(❌)가 다음 수를 고민하고 있습니다...")
    else:
      st.info(
          f"🎯 현재 진행 턴: **{st.session_state.ttt_moves}수** | "
          "👤 **플레이어(🔵)** 차례입니다!"
      )
  with col_btn:
    if st.button("🔄 새 게임 시작", use_container_width=True):
      reset_tictactoe_game()  # 상태 초기화 후
      st.rerun()  # 화면을 즉시 새로고침

  st.divider()

  # 3. 정사각형 3x3 버튼 격자 보드판 출력 (key로 전용 정사각형 CSS 적용)
  board = st.session_state.ttt_board  # 현재 보드판 상태 가져오기
  with st.container(key="ttt_board_box"):
    for row in range(3):  # 0~2행 반복
      cols = st.columns(3)  # 한 행에 3개의 열 생성
      for col in range(3):  # 0~2열 반복
        idx = row * 3 + col  # 2차원 좌표(row, col)를 1차원 인덱스(0~8)로 변환
        cell_value = board[idx]  # 해당 칸에 놓인 말("", "O", "X")

        # 플레이어(🔵 파란색)와 AI(❌ 빨간색)를 색과 모양으로 명확히 구분
        if cell_value == "O":
          label = "🔵"
        elif cell_value == "X":
          label = "❌"
        else:
          label = " "  # 빈 칸은 깔끔한 여백으로 표시

        with cols[col]:
          # 이미 말이 놓였거나, 게임이 끝났거나, AI가 생각하는 중이면 버튼 잠금
          is_disabled = (
              (cell_value != "")
              or st.session_state.ttt_game_over
              or st.session_state.ttt_ai_thinking
          )
          if st.button(
              label,
              key=f"ttt_cell_{idx}",  # 각 칸 버튼의 고유 키
              disabled=is_disabled,
              use_container_width=True,
          ):
            handle_player_move(idx)  # 플레이어 착수 처리
            st.rerun()  # 먼저 플레이어 말을 화면에 즉시 표시

  # 4. 플레이어 착수가 화면에 표시된 직후, 짧은 딜레이를 두고 AI 착수 실행
  if st.session_state.ttt_ai_thinking and not st.session_state.ttt_game_over:
    time.sleep(AI_DELAY_SECONDS)  # 0.6초 대기하여 자연스러운 대전 느낌 연출
    handle_ai_move()  # AI 착수 및 승패 판정 실행
    st.rerun()  # AI가 둔 말을 화면에 반영

  st.divider()

  # 5. 게임이 종료되었을 때 결과 배너 출력 영역
  if st.session_state.ttt_game_over:
    if st.session_state.ttt_winner == "O":
      moves = st.session_state.ttt_moves
      st.balloons()  # 승리 축하 풍선 애니메이션
      st.success(
          f"🎉 축하합니다! 플레이어(🔵)가 **{moves}수** 만에 AI(❌)를 이겼습니다! (JSON 기록 완료)"
      )
    elif st.session_state.ttt_winner == "X":
      st.error("💥 아쉽습니다! AI(❌)가 먼저 3목을 완성했습니다.")
    else:
      st.warning("🤝 무승부입니다! 팽팽한 승부였네요.")
