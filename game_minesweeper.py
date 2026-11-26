from collections import deque  # 빈 칸(0) 연쇄 열기를 위한 큐(BFS) 자료구조
import random  # 지뢰 위치 무작위 배치 및 힌트 칸 선택을 위한 기본 모듈
import data_manager as dm  # 게임 종료 시 전적을 game_records.json에 저장하는 공용 모듈
import streamlit as st  # 웹 UI 구성 및 상태 관리를 위한 Streamlit 라이브러리

# 보드판 내부 값 상수 (-1은 지뢰, 0~8은 주변 8방향 지뢰 개수)
MINE = -1

# 난이도별 (행, 열, 지뢰 개수) 설정 — 지뢰 밀도 약 16%로 추리 밸런스 유지
DIFFICULTIES = {
    "초급 (5×5 · 지뢰 4개)": (5, 5, 4),
    "중급 (7×7 · 지뢰 8개)": (7, 7, 8),
    "고급 (9×9 · 지뢰 13개)": (9, 9, 13),
}
DEFAULT_DIFFICULTY = "중급 (7×7 · 지뢰 8개)"

# 상하좌우 및 대각선 8방향 탐색용 좌표 변화량
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def create_empty_board(rows: int, cols: int) -> list[list[int]]:
  """지뢰 배치 전 모든 칸이 0으로 초기화된 빈 2차원 보드판을 반환하는 함수"""
  return [[0 for _ in range(cols)] for _ in range(rows)]


def generate_board_safe(
    rows: int, cols: int, num_mines: int, safe_r: int, safe_c: int
) -> list[list[int]]:
  """첫 클릭 좌표(safe_r, safe_c)와 주변 8칸을 피해 지뢰를 배치하고 힌트 숫자를 계산하는 함수"""
  board = create_empty_board(rows, cols)

  # 1. 첫 클릭 칸과 인접 8칸을 안전 구역으로 지정 (첫 클릭 시 항상 0이 열려 시원하게 시작됨)
  safe_zone = {
      (safe_r + dr, safe_c + dc)
      for dr in (-1, 0, 1)
      for dc in (-1, 0, 1)
      if 0 <= safe_r + dr < rows and 0 <= safe_c + dc < cols
  }

  candidates = [
      (r, c)
      for r in range(rows)
      for c in range(cols)
      if (r, c) not in safe_zone
  ]
  if len(candidates) < num_mines:
    candidates = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (r, c) != (safe_r, safe_c)
    ]

  # 2. 후보 좌표 중에서 무작위로 지뢰 위치 선택
  mine_positions = random.sample(candidates, num_mines)
  for mr, mc in mine_positions:
    board[mr][mc] = MINE

  # 3. 지뢰가 아닌 모든 칸에 대해 주변 8방향의 지뢰 개수(0~8) 계산
  for r in range(rows):
    for c in range(cols):
      if board[r][c] == MINE:
        continue
      count = 0
      for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == MINE:
          count += 1
      board[r][c] = count

  return board


def init_minesweeper_state():
  """지뢰찾기 게임에 필요한 세션 상태 변수(ms_*)를 처음 한 번 초기화하는 함수"""
  if "game_data" not in st.session_state:
    st.session_state.game_data = dm.load_data()

  if "ms_difficulty" not in st.session_state:
    st.session_state.ms_difficulty = DEFAULT_DIFFICULTY

  rows, cols, mines = DIFFICULTIES[st.session_state.ms_difficulty]

  if "ms_rows" not in st.session_state:
    st.session_state.ms_rows = rows
  if "ms_cols" not in st.session_state:
    st.session_state.ms_cols = cols
  if "ms_mines" not in st.session_state:
    st.session_state.ms_mines = mines

  # 첫 클릭 전까지는 빈 보드 상태로 대기 (첫 클릭 안전 보장용)
  if "ms_board" not in st.session_state:
    st.session_state.ms_board = create_empty_board(rows, cols)
  if "ms_board_ready" not in st.session_state:
    st.session_state.ms_board_ready = False

  if "ms_revealed" not in st.session_state:
    st.session_state.ms_revealed = [
        [False for _ in range(cols)] for _ in range(rows)
    ]
  if "ms_flagged" not in st.session_state:
    st.session_state.ms_flagged = [
        [False for _ in range(cols)] for _ in range(rows)
    ]

  if "ms_mode" not in st.session_state:
    st.session_state.ms_mode = "reveal"

  # 힌트 1회 사용 여부 및 게임 종료·승패 상태
  if "ms_hint_used" not in st.session_state:
    st.session_state.ms_hint_used = False
  if "ms_game_over" not in st.session_state:
    st.session_state.ms_game_over = False
  if "ms_is_win" not in st.session_state:
    st.session_state.ms_is_win = False
  if "ms_exploded_pos" not in st.session_state:
    st.session_state.ms_exploded_pos = None


def reset_minesweeper_game(difficulty_name: str = None):
  """새 게임 시작 또는 난이도 변경 시 보드판과 힌트·승패 상태를 초기화하는 함수"""
  if difficulty_name is not None:
    st.session_state.ms_difficulty = difficulty_name

  rows, cols, mines = DIFFICULTIES[st.session_state.ms_difficulty]
  st.session_state.ms_rows = rows
  st.session_state.ms_cols = cols
  st.session_state.ms_mines = mines

  st.session_state.ms_board = create_empty_board(rows, cols)
  st.session_state.ms_board_ready = False
  st.session_state.ms_revealed = [
      [False for _ in range(cols)] for _ in range(rows)
  ]
  st.session_state.ms_flagged = [
      [False for _ in range(cols)] for _ in range(rows)
  ]
  st.session_state.ms_hint_used = False
  st.session_state.ms_game_over = False
  st.session_state.ms_is_win = False
  st.session_state.ms_exploded_pos = None


def apply_board_style(cols: int):
  """칸 개수에 맞춰 정사각형 격자 보드판을 깔끔하게 정렬하는 CSS 스타일 함수"""
  max_width = cols * 64
  st.markdown(
      f"""
      <style>
      .st-key-ms_board_box {{
        max-width: {max_width}px;
        margin: 0 auto;
      }}
      /* 열 간격을 좁혀 지뢰찾기 타일 느낌 연출 */
      .st-key-ms_board_box [data-testid="stHorizontalBlock"] {{
        gap: 0.35rem;
        margin-bottom: 0.35rem;
      }}
      .st-key-ms_board_box button {{
        aspect-ratio: 1 / 1;
        width: 100%;
        min-height: 46px;
        padding: 0 !important;
        border-radius: 8px;
      }}
      .st-key-ms_board_box button p {{
        font-size: 1.05rem;
        font-weight: 800;
        line-height: 1;
        margin: 0;
      }}
      /* 열린 칸(disabled)은 평평하게 들어가 보이되 숫자는 선명하게 유지 */
      .st-key-ms_board_box button:disabled {{
        background-color: rgba(128, 128, 128, 0.14) !important;
        border-color: rgba(128, 128, 128, 0.18) !important;
        opacity: 0.92 !important;
      }}
      </style>
      """,
      unsafe_allow_html=True,
  )


def reveal_cell(r: int, c: int):
  """특정 칸(r, c)을 열고, 값이 0(주변 지뢰 없음)이면 BFS 큐로 인접 빈 칸들을 한 번에 여는 함수"""
  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols
  board = st.session_state.ms_board
  revealed = st.session_state.ms_revealed
  flagged = st.session_state.ms_flagged

  if revealed[r][c] or flagged[r][c]:
    return

  queue = deque([(r, c)])
  revealed[r][c] = True

  while queue:
    curr_r, curr_c = queue.popleft()
    # 현재 칸이 0일 때만 주변 8방향으로 연쇄 확장
    if board[curr_r][curr_c] == 0:
      for dr, dc in DIRECTIONS:
        nr, nc = curr_r + dr, curr_c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
          if (
              not revealed[nr][nc]
              and not flagged[nr][nc]
              and board[nr][nc] != MINE
          ):
            revealed[nr][nc] = True
            if board[nr][nc] == 0:
              queue.append((nr, nc))


def check_win() -> bool:
  """지뢰가 아닌 모든 안전한 칸이 열렸는지 검사하여 승리 여부를 반환하는 함수"""
  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols
  safe_target = rows * cols - st.session_state.ms_mines

  opened_safe = sum(
      1
      for r in range(rows)
      for c in range(cols)
      if st.session_state.ms_revealed[r][c]
      and st.session_state.ms_board[r][c] != MINE
  )
  return opened_safe == safe_target


def finish_game(is_win: bool):
  """게임 승리 또는 패배 시 보드 상태를 정리하고 JSON 전적 파일에 저장하는 함수"""
  st.session_state.ms_game_over = True
  st.session_state.ms_is_win = is_win

  if is_win:
    # 승리 시 남은 지뢰 칸에 자동으로 깃발 표시
    for r in range(st.session_state.ms_rows):
      for c in range(st.session_state.ms_cols):
        if st.session_state.ms_board[r][c] == MINE:
          st.session_state.ms_flagged[r][c] = True

    dm.record_game_result("minesweeper", is_win=True)
  else:
    # 패배 시 숨겨진 모든 지뢰 위치를 공개
    for r in range(st.session_state.ms_rows):
      for c in range(st.session_state.ms_cols):
        if st.session_state.ms_board[r][c] == MINE:
          st.session_state.ms_revealed[r][c] = True

    dm.record_game_result("minesweeper", is_win=False)


def handle_cell_click(r: int, c: int):
  """사용자가 보드판의 (r, c) 칸을 클릭했을 때 모드에 따라 열기·깃발·승패를 처리하는 함수"""
  if st.session_state.ms_game_over:
    return

  # 1. 깃발 모드: 닫힌 칸에 깃발을 꽂거나 해제
  if st.session_state.ms_mode == "flag":
    if not st.session_state.ms_revealed[r][c]:
      st.session_state.ms_flagged[r][c] = not st.session_state.ms_flagged[r][c]
    return

  # 2. 열기 모드: 깃발이 꽂힌 칸은 실수 방지를 위해 무시
  if st.session_state.ms_flagged[r][c] or st.session_state.ms_revealed[r][c]:
    return

  # 첫 칸 열기 시점에 지뢰를 배치해 '첫 클릭 안전 보장'
  if not st.session_state.ms_board_ready:
    st.session_state.ms_board = generate_board_safe(
        st.session_state.ms_rows,
        st.session_state.ms_cols,
        st.session_state.ms_mines,
        r,
        c,
    )
    st.session_state.ms_board_ready = True

  # 지뢰를 밟은 경우 패배 처리
  if st.session_state.ms_board[r][c] == MINE:
    st.session_state.ms_exploded_pos = (r, c)
    finish_game(is_win=False)
    return

  # 안전한 칸 열기 및 승리 여부 확인
  reveal_cell(r, c)
  if check_win():
    finish_game(is_win=True)


def use_hint():
  """판당 1회 사용할 수 있는 찬스로, 안전한 미개방 칸 1개를 자동으로 열어주는 함수"""
  if st.session_state.ms_game_over or st.session_state.ms_hint_used:
    return

  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols

  # 아직 첫 클릭 전이라면 중앙 칸 기준으로 안전 보드를 생성
  if not st.session_state.ms_board_ready:
    center_r, center_c = rows // 2, cols // 2
    st.session_state.ms_board = generate_board_safe(
        rows, cols, st.session_state.ms_mines, center_r, center_c
    )
    st.session_state.ms_board_ready = True
    target_r, target_c = center_r, center_c
  else:
    # 이미 열린 숫자 칸 주변(경계선)에 있는 안전 칸을 우선 선택해 실질적인 추리 도움을 제공
    frontier_safe = []
    all_safe = []
    for r in range(rows):
      for c in range(cols):
        if (
            not st.session_state.ms_revealed[r][c]
            and st.session_state.ms_board[r][c] != MINE
        ):
          all_safe.append((r, c))
          if any(
              0 <= r + dr < rows
              and 0 <= c + dc < cols
              and st.session_state.ms_revealed[r + dr][c + dc]
              for dr, dc in DIRECTIONS
          ):
            frontier_safe.append((r, c))

    if not all_safe:
      return
    target_r, target_c = random.choice(
        frontier_safe if frontier_safe else all_safe
    )

  # 해당 칸에 잘못 꽂힌 깃발이 있었다면 해제 후 오픈
  st.session_state.ms_flagged[target_r][target_c] = False
  st.session_state.ms_hint_used = True

  reveal_cell(target_r, target_c)
  if check_win():
    finish_game(is_win=True)


def get_cell_label(r: int, c: int) -> str:
  """현재 칸 상태에 따라 버튼에 표시할 아이콘 또는 숫자를 반환하는 함수"""
  is_revealed = st.session_state.ms_revealed[r][c]
  is_flagged = st.session_state.ms_flagged[r][c]
  value = st.session_state.ms_board[r][c]

  # 게임 종료 후 지뢰가 아닌 곳에 잘못 꽂은 깃발 표시
  if st.session_state.ms_game_over and is_flagged and value != MINE:
    return "❌"

  if not is_revealed:
    return "🚩" if is_flagged else " "

  if value == MINE:
    if st.session_state.ms_exploded_pos == (r, c):
      return "💥"
    return "💣"

  if value == 0:
    return " "
  return str(value)


def run():
  """main.py에서 메뉴를 선택했을 때 호출되는 지뢰찾기 메인 실행 함수"""
  init_minesweeper_state()

  st.header("💣 3. 지뢰찾기")
  st.markdown(
      "숫자 힌트로 지뢰 위치를 추리해 **모든 안전한 칸**을 열어보세요! "
      "*(첫 번째 클릭은 항상 안전합니다)*"
  )

  # 1단 컨트롤 바: 난이도 선택 / 남은 지뢰 수 / 새 게임 버튼
  col_diff, col_mines, col_reset = st.columns([1.4, 1.6, 1])
  with col_diff:
    selected_diff = st.selectbox(
        "난이도 선택",
        options=list(DIFFICULTIES.keys()),
        index=list(DIFFICULTIES.keys()).index(st.session_state.ms_difficulty),
        label_visibility="collapsed",
    )
    if selected_diff != st.session_state.ms_difficulty:
      reset_minesweeper_game(selected_diff)
      st.rerun()

  with col_mines:
    flag_count = sum(
        sum(1 for cell in row if cell) for row in st.session_state.ms_flagged
    )
    remaining_mines = st.session_state.ms_mines - flag_count
    st.info(
        f"🚩 남은 지뢰: **{remaining_mines}개** / 총 {st.session_state.ms_mines}개"
    )

  with col_reset:
    if st.button("🔄 새 게임 시작", use_container_width=True):
      reset_minesweeper_game()
      st.rerun()

  # 2단 컨트롤 바: 열기·깃발 모드 전환 / 힌트 1회 버튼
  col_mode, col_hint = st.columns([3, 1])
  with col_mode:
    mode_choice = st.radio(
        "클릭 모드",
        options=["reveal", "flag"],
        index=0 if st.session_state.ms_mode == "reveal" else 1,
        format_func=lambda x: "🔍 칸 열기 모드"
        if x == "reveal"
        else "🚩 깃발 꽂기 모드",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.ms_mode = mode_choice

  with col_hint:
    hint_label = (
        "💡 힌트 사용 완료" if st.session_state.ms_hint_used else "💡 힌트 1회"
    )
    if st.button(
        hint_label,
        disabled=st.session_state.ms_hint_used or st.session_state.ms_game_over,
        use_container_width=True,
    ):
      use_hint()
      st.rerun()

  st.divider()

  # 정사각형 보드판 스타일 적용 및 격자 버튼 렌더링
  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols
  apply_board_style(cols)

  with st.container(key="ms_board_box"):
    for r in range(rows):
      grid_cols = st.columns(cols)
      for c in range(cols):
        with grid_cols[c]:
          label = get_cell_label(r, c)
          is_disabled = (
              st.session_state.ms_revealed[r][c]
              or st.session_state.ms_game_over
          )
          if st.button(
              label,
              key=f"ms_cell_{r}_{c}",
              disabled=is_disabled,
              use_container_width=True,
          ):
            handle_cell_click(r, c)
            st.rerun()

  st.divider()

  # 게임 종료 시 승패 결과 배너 출력
  if st.session_state.ms_game_over:
    if st.session_state.ms_is_win:
      st.balloons()
      st.success(
          "🎉 축하합니다! 모든 지뢰를 완벽히 피하고 클리어했습니다! (JSON 기록 완료)"
      )
    else:
      st.error(
          "💥 지뢰(💥)를 밟았습니다! 숨겨진 지뢰(💣) 위치를 확인하고 다시 도전해 보세요."
      )


if __name__ == "__main__":
  run()
