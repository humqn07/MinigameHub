from collections import deque  # 빈 칸(0) 연쇄 열기 및 클러스터 크기 분석을 위한 큐(BFS)
import random  # 지뢰 배치 후보 생성 및 안개 타일 선택을 위한 기본 모듈
import data_manager as dm  # 게임 종료 시 전적을 game_records.json에 저장하는 공용 모듈
import streamlit as st  # 웹 UI 구성 및 상태 관리를 위한 Streamlit 라이브러리

# 보드판 내부 값 상수 (-1은 지뢰, 0~8은 주변 8방향 지뢰 개수)
MINE = -1

# 보드 생성 시 빈칸(0) 대량 개방을 억제하기 위해 비교할 후보 보드 개수
CANDIDATE_TRIALS = 12

# 난이도별 (행, 열, 지뢰 수, 안개[?] 타일 수, 첫 클릭 안전 반경 모드)
# 기존(25 / 49 / 81칸) 대비 칸 수를 약 2.5배로 확대하고 지뢰 밀도를 19~22.5%로 상향
DIFFICULTIES = {
    "초급 (8×8 · 64칸 · 지뢰 12개)": (8, 8, 12, 2, "cross"),
    "중급 (11×11 · 121칸 · 지뢰 25개)": (11, 11, 25, 5, "tight"),
    "고급 (14×14 · 196칸 · 지뢰 44개)": (14, 14, 44, 9, "single"),
}
DEFAULT_DIFFICULTY = "중급 (11×11 · 121칸 · 지뢰 25개)"

# 상하좌우 및 대각선 8방향 탐색용 좌표 변화량
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def create_empty_board(rows: int, cols: int) -> list[list[int]]:
  """지뢰 배치 전 모든 칸이 0으로 초기화된 빈 2차원 보드판을 반환하는 함수"""
  return [[0 for _ in range(cols)] for _ in range(rows)]


def build_safe_zone(
    rows: int, cols: int, safe_r: int, safe_c: int, safe_mode: str
) -> set[tuple[int, int]]:
  """난이도에 따라 첫 클릭 시 보호할 안전 구역 좌표를 차등 생성하는 함수"""
  # 고급("single"): 오직 첫 클릭한 단 1칸만 지뢰에서 보호 (첫 수부터 숫자 추리 강제)
  if safe_mode == "single":
    return {(safe_r, safe_c)}

  # 상하좌우 인접 칸 목록
  ortho_neighbors = [
      (safe_r + dr, safe_c + dc)
      for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
      if 0 <= safe_r + dr < rows and 0 <= safe_c + dc < cols
  ]

  # 중급("tight"): 첫 클릭 칸 + 무작위 인접 2칸만 최소한으로 보호
  if safe_mode == "tight":
    picked = random.sample(ortho_neighbors, min(2, len(ortho_neighbors)))
    return {(safe_r, safe_c), *picked}

  # 초급("cross"): 첫 클릭 칸 + 상하좌우 십자(최대 5칸) 보호 (기존 9칸보다 축소)
  return {(safe_r, safe_c), *ortho_neighbors}


def measure_board_easiness(board: list[list[int]], start_r: int, start_c: int) -> tuple[int, int]:
  """
  후보 보드의 '쉬움 정도'를 측정하는 평가 함수 (낮을수록 더 어렵고 촘촘한 보드)
  1순위: 첫 클릭으로 한 번에 열리는 칸 수 (초기 공짜 개방 억제)
  2순위: 보드 전체의 빈칸(0) 총개수 (거대 빈 공간 억제, 숫자 교차 추리 유도)
  """
  rows = len(board)
  cols = len(board[0])

  # 첫 클릭 시 BFS로 열리는 영역 크기 시뮬레이션
  visited = {(start_r, start_c)}
  if board[start_r][start_c] == 0:
    queue = deque([(start_r, start_c)])
    while queue:
      cr, cc = queue.popleft()
      if board[cr][cc] == 0:
        for dr, dc in DIRECTIONS:
          nr, nc = cr + dr, cc + dc
          if (
              0 <= nr < rows
              and 0 <= nc < cols
              and (nr, nc) not in visited
              and board[nr][nc] != MINE
          ):
            visited.add((nr, nc))
            if board[nr][nc] == 0:
              queue.append((nr, nc))

  zero_total = sum(
      1 for r in range(rows) for c in range(cols) if board[r][c] == 0
  )
  return len(visited), zero_total


def select_fog_cells(
    board: list[list[int]], fog_count: int, safe_r: int, safe_c: int
) -> set[tuple[int, int]]:
  """
  숫자 힌트 중 일부를 '?'(안개 타일)로 가려 교차 추리를 강제하는 좌표를 선정하는 함수
  - 첫 클릭 칸과 지뢰, 빈칸(0)은 제외하며 안개 타일끼리 서로 붙지 않도록 배치해 추리 가능성 유지
  """
  rows = len(board)
  cols = len(board[0])
  candidates = [
      (r, c)
      for r in range(rows)
      for c in range(cols)
      if board[r][c] >= 1 and (r, c) != (safe_r, safe_c)
  ]
  random.shuffle(candidates)

  fog_cells: set[tuple[int, int]] = set()
  for r, c in candidates:
    if len(fog_cells) >= fog_count:
      break
    # 안개 칸이 연속으로 뭉치면 추리가 불가능해지므로 서로 인접하지 않게 이격 배치
    if all(abs(r - fr) > 1 or abs(c - fc) > 1 for fr, fc in fog_cells):
      fog_cells.add((r, c))

  return fog_cells


def generate_challenging_board(
    rows: int,
    cols: int,
    num_mines: int,
    fog_count: int,
    safe_mode: str,
    safe_r: int,
    safe_c: int,
) -> tuple[list[list[int]], set[tuple[int, int]]]:
  """
  여러 후보 보드를 생성해 시뮬레이션한 뒤, 공짜 연쇄 개방이 가장 적고
  숫자 밀도가 높은 가장 까다로운 보드와 안개('?') 좌표를 반환하는 함수
  """
  safe_zone = build_safe_zone(rows, cols, safe_r, safe_c, safe_mode)
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

  best_board = None
  best_score = None

  # CANDIDATE_TRIALS개의 보드를 만들어 가장 덜 쉽게 열리는(가장 어려운) 보드를 채택
  for _ in range(CANDIDATE_TRIALS):
    board = create_empty_board(rows, cols)
    for mr, mc in random.sample(candidates, num_mines):
      board[mr][mc] = MINE

    for r in range(rows):
      for c in range(cols):
        if board[r][c] == MINE:
          continue
        board[r][c] = sum(
            1
            for dr, dc in DIRECTIONS
            if 0 <= r + dr < rows
            and 0 <= c + dc < cols
            and board[r + dr][c + dc] == MINE
        )

    easiness = measure_board_easiness(board, safe_r, safe_c)
    if best_score is None or easiness < best_score:
      best_score = easiness
      best_board = board

  fog_cells = select_fog_cells(best_board, fog_count, safe_r, safe_c)
  return best_board, fog_cells


def init_minesweeper_state():
  """지뢰찾기 게임에 필요한 세션 상태 변수(ms_*)를 처음 한 번 초기화하는 함수"""
  if "game_data" not in st.session_state:
    st.session_state.game_data = dm.load_data()

  if (
      "ms_difficulty" not in st.session_state
      or st.session_state.ms_difficulty not in DIFFICULTIES
  ):
    st.session_state.ms_difficulty = DEFAULT_DIFFICULTY

  rows, cols, mines, fog_cnt, safe_mode = DIFFICULTIES[
      st.session_state.ms_difficulty
  ]

  if "ms_rows" not in st.session_state:
    st.session_state.ms_rows = rows
  if "ms_cols" not in st.session_state:
    st.session_state.ms_cols = cols
  if "ms_mines" not in st.session_state:
    st.session_state.ms_mines = mines
  if "ms_fog_count" not in st.session_state:
    st.session_state.ms_fog_count = fog_cnt
  if "ms_safe_mode" not in st.session_state:
    st.session_state.ms_safe_mode = safe_mode

  if "ms_mode" not in st.session_state:
    st.session_state.ms_mode = "reveal"

  # 기존 세션의 보드 크기와 현재 난이도 설정이 다르면 즉시 재초기화
  if (
      "ms_board" not in st.session_state
      or len(st.session_state.ms_board) != st.session_state.ms_rows
      or len(st.session_state.ms_board[0]) != st.session_state.ms_cols
  ):
    reset_minesweeper_game(st.session_state.ms_difficulty)
    return

  if "ms_board_ready" not in st.session_state:
    st.session_state.ms_board_ready = False
  if "ms_fog_cells" not in st.session_state:
    st.session_state.ms_fog_cells = set()
  if "ms_revealed" not in st.session_state:
    st.session_state.ms_revealed = [
        [False for _ in range(cols)] for _ in range(rows)
    ]
  if "ms_flagged" not in st.session_state:
    st.session_state.ms_flagged = [
        [False for _ in range(cols)] for _ in range(rows)
    ]
  if "ms_hint_used" not in st.session_state:
    st.session_state.ms_hint_used = False
  if "ms_flag_warning" not in st.session_state:
    st.session_state.ms_flag_warning = False
  if "ms_game_over" not in st.session_state:
    st.session_state.ms_game_over = False
  if "ms_is_win" not in st.session_state:
    st.session_state.ms_is_win = False
  if "ms_exploded_pos" not in st.session_state:
    st.session_state.ms_exploded_pos = None


def reset_minesweeper_game(difficulty_name: str = None):
  """새 게임 시작 또는 난이도 변경 시 보드판과 안개·힌트·승패 상태를 초기화하는 함수"""
  if difficulty_name is not None:
    st.session_state.ms_difficulty = difficulty_name

  rows, cols, mines, fog_cnt, safe_mode = DIFFICULTIES[
      st.session_state.ms_difficulty
  ]
  st.session_state.ms_rows = rows
  st.session_state.ms_cols = cols
  st.session_state.ms_mines = mines
  st.session_state.ms_fog_count = fog_cnt
  st.session_state.ms_safe_mode = safe_mode

  st.session_state.ms_board = create_empty_board(rows, cols)
  st.session_state.ms_board_ready = False
  st.session_state.ms_fog_cells = set()
  st.session_state.ms_revealed = [
      [False for _ in range(cols)] for _ in range(rows)
  ]
  st.session_state.ms_flagged = [
      [False for _ in range(cols)] for _ in range(rows)
  ]
  if "ms_mode" not in st.session_state:
    st.session_state.ms_mode = "reveal"
  st.session_state.ms_hint_used = False
  st.session_state.ms_flag_warning = False
  st.session_state.ms_game_over = False
  st.session_state.ms_is_win = False
  st.session_state.ms_exploded_pos = None


def apply_board_style(cols: int):
  """8×8 ~ 14×14 대형 격자 보드가 한 화면에 정사각형으로 촘촘히 들어오도록 조정하는 CSS"""
  if cols >= 14:
    cell_px, step_px, font_rem = 34, 42, "0.92rem"
  elif cols >= 11:
    cell_px, step_px, font_rem = 38, 46, "0.98rem"
  else:
    cell_px, step_px, font_rem = 44, 52, "1.05rem"

  max_width = cols * step_px
  st.markdown(
      f"""
      <style>
      .st-key-ms_board_box {{
        max-width: {max_width}px;
        margin: 0 auto;
      }}
      .st-key-ms_board_box [data-testid="stHorizontalBlock"] {{
        gap: 0.2rem !important;
        margin-bottom: 0.2rem !important;
        flex-wrap: nowrap !important;
      }}
      .st-key-ms_board_box [data-testid="stColumn"] {{
        min-width: 0 !important;
        flex: 1 1 0 !important;
      }}
      .st-key-ms_board_box button {{
        aspect-ratio: 1 / 1;
        width: 100%;
        min-height: {cell_px}px;
        padding: 0 !important;
        border-radius: 6px;
      }}
      .st-key-ms_board_box button p {{
        font-size: {font_rem};
        font-weight: 800;
        line-height: 1;
        margin: 0;
      }}
      /* 이미 열린 칸(disabled)은 평평하게 들어가 보이되 숫자와 기호는 선명하게 유지 */
      .st-key-ms_board_box button:disabled {{
        background-color: rgba(128, 128, 128, 0.15) !important;
        border-color: rgba(128, 128, 128, 0.2) !important;
        opacity: 0.94 !important;
      }}
      </style>
      """,
      unsafe_allow_html=True,
  )


def count_total_flags() -> int:
  """현재 보드판 전체에 꽂힌 깃발 개수를 반환하는 함수"""
  return sum(
      sum(1 for cell in row if cell) for row in st.session_state.ms_flagged
  )


def is_chord_ready(r: int, c: int) -> bool:
  """
  열린 숫자 칸(r, c)이 '코드 열기(Chording)'가 가능한 상태인지 확인하는 함수
  - 조건: 이미 열려 있고, 안개('?') 칸이 아닌 숫자(1~8)이며,
    주변 깃발 수가 해당 숫자와 정확히 일치하고 아직 닫힌(무깃발) 인접 칸이 남아 있을 때
  """
  if st.session_state.ms_game_over or st.session_state.ms_mode != "reveal":
    return False
  if not st.session_state.ms_revealed[r][c]:
    return False
  if (r, c) in st.session_state.ms_fog_cells:
    return False

  val = st.session_state.ms_board[r][c]
  if val <= 0:
    return False

  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols
  adj_flags = 0
  closed_unflagged = 0

  for dr, dc in DIRECTIONS:
    nr, nc = r + dr, c + dc
    if 0 <= nr < rows and 0 <= nc < cols:
      if st.session_state.ms_flagged[nr][nc]:
        adj_flags += 1
      elif not st.session_state.ms_revealed[nr][nc]:
        closed_unflagged += 1

  return adj_flags == val and closed_unflagged > 0


def reveal_cell(r: int, c: int):
  """특정 칸(r, c)을 열고 값이 0이면 BFS로 인접 안전 영역을 연쇄 개방하는 함수"""
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
    # 안개('?') 칸은 항상 1 이상의 숫자 칸이므로 0일 때만 주변으로 연쇄 확장됨
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


def chord_reveal(r: int, c: int):
  """
  열린 숫자 칸을 다시 클릭했을 때 주변 무깃발 칸들을 동시에 여는 '코드 열기' 함수
  - 만약 주변에 깃발을 잘못 꽂아 실제 지뢰가 노출되어 있다면 즉시 폭발(패배)함!
  """
  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols

  for dr, dc in DIRECTIONS:
    nr, nc = r + dr, c + dc
    if 0 <= nr < rows and 0 <= nc < cols:
      if (
          not st.session_state.ms_revealed[nr][nc]
          and not st.session_state.ms_flagged[nr][nc]
      ):
        if st.session_state.ms_board[nr][nc] == MINE:
          st.session_state.ms_exploded_pos = (nr, nc)
          finish_game(is_win=False)
          return
        reveal_cell(nr, nc)

  if check_win():
    finish_game(is_win=True)


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
    for r in range(st.session_state.ms_rows):
      for c in range(st.session_state.ms_cols):
        if st.session_state.ms_board[r][c] == MINE:
          st.session_state.ms_flagged[r][c] = True

    dm.record_game_result("minesweeper", is_win=True)
  else:
    for r in range(st.session_state.ms_rows):
      for c in range(st.session_state.ms_cols):
        if st.session_state.ms_board[r][c] == MINE:
          st.session_state.ms_revealed[r][c] = True

    dm.record_game_result("minesweeper", is_win=False)


def handle_cell_click(r: int, c: int):
  """사용자가 보드판의 (r, c) 칸을 클릭했을 때 열기·깃발·코드열기·승패를 처리하는 함수"""
  if st.session_state.ms_game_over:
    return

  st.session_state.ms_flag_warning = False

  # 1. 이미 열린 숫자 칸을 클릭한 경우 -> 코드 열기(Chording) 수행
  if st.session_state.ms_revealed[r][c]:
    if is_chord_ready(r, c):
      chord_reveal(r, c)
    return

  # 2. 깃발 모드: 총 지뢰 개수를 초과해서 무분별하게 깃발을 꽂지 못하도록 제한
  if st.session_state.ms_mode == "flag":
    if st.session_state.ms_flagged[r][c]:
      st.session_state.ms_flagged[r][c] = False
    else:
      if count_total_flags() >= st.session_state.ms_mines:
        st.session_state.ms_flag_warning = True
      else:
        st.session_state.ms_flagged[r][c] = True
    return

  # 3. 열기 모드: 깃발이 꽂힌 칸은 오클릭 방지를 위해 무시
  if st.session_state.ms_flagged[r][c]:
    return

  # 첫 칸 열기 시점에 고난도 전략 보드 및 안개('?') 타일 생성
  if not st.session_state.ms_board_ready:
    board, fog_cells = generate_challenging_board(
        st.session_state.ms_rows,
        st.session_state.ms_cols,
        st.session_state.ms_mines,
        st.session_state.ms_fog_count,
        st.session_state.ms_safe_mode,
        r,
        c,
    )
    st.session_state.ms_board = board
    st.session_state.ms_fog_cells = fog_cells
    st.session_state.ms_board_ready = True

  # 지뢰를 밟은 경우 즉시 패배
  if st.session_state.ms_board[r][c] == MINE:
    st.session_state.ms_exploded_pos = (r, c)
    finish_game(is_win=False)
    return

  reveal_cell(r, c)
  if check_win():
    finish_game(is_win=True)


def use_hint():
  """
  판당 단 1회 사용 가능한 돌파 찬스:
  안개('?') 주변이나 고위험 숫자(3 이상) 경계선의 안전 칸을 최우선 탐색해 열어주는 함수
  """
  if st.session_state.ms_game_over or st.session_state.ms_hint_used:
    return

  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols
  st.session_state.ms_flag_warning = False

  if not st.session_state.ms_board_ready:
    center_r, center_c = rows // 2, cols // 2
    board, fog_cells = generate_challenging_board(
        rows,
        cols,
        st.session_state.ms_mines,
        st.session_state.ms_fog_count,
        st.session_state.ms_safe_mode,
        center_r,
        center_c,
    )
    st.session_state.ms_board = board
    st.session_state.ms_fog_cells = fog_cells
    st.session_state.ms_board_ready = True
    target_r, target_c = center_r, center_c
  else:
    hard_frontier = []  # 안개('?')나 고숫자(3+)에 인접한 까다로운 경계 안전 칸
    normal_frontier = []  # 일반 열린 숫자에 인접한 경계 안전 칸
    all_safe = []

    for r in range(rows):
      for c in range(cols):
        if (
            not st.session_state.ms_revealed[r][c]
            and st.session_state.ms_board[r][c] != MINE
        ):
          all_safe.append((r, c))
          opened_neighbors = [
              (r + dr, c + dc)
              for dr, dc in DIRECTIONS
              if 0 <= r + dr < rows
              and 0 <= c + dc < cols
              and st.session_state.ms_revealed[r + dr][c + dc]
          ]
          if opened_neighbors:
            normal_frontier.append((r, c))
            if any(
                nb in st.session_state.ms_fog_cells
                or st.session_state.ms_board[nb[0]][nb[1]] >= 3
                for nb in opened_neighbors
            ):
              hard_frontier.append((r, c))

    if not all_safe:
      return
    pool = (
        hard_frontier
        if hard_frontier
        else (normal_frontier if normal_frontier else all_safe)
    )
    target_r, target_c = random.choice(pool)

  # 힌트로 열린 칸이 안개('?') 칸이었다면 안개까지 걷어내 정확한 숫자를 알려줌
  st.session_state.ms_fog_cells.discard((target_r, target_c))
  st.session_state.ms_flagged[target_r][target_c] = False
  st.session_state.ms_hint_used = True

  reveal_cell(target_r, target_c)
  if check_win():
    finish_game(is_win=True)


def get_cell_label(r: int, c: int) -> str:
  """현재 칸 상태(닫힘, 깃발, 안개 '?', 코드열기 가능, 숫자, 지뢰)에 따른 표시 문자열 반환"""
  is_revealed = st.session_state.ms_revealed[r][c]
  is_flagged = st.session_state.ms_flagged[r][c]
  value = st.session_state.ms_board[r][c]

  # 게임 종료 시 잘못 꽂은 깃발 표시
  if st.session_state.ms_game_over and is_flagged and value != MINE:
    return "❌"

  if not is_revealed:
    return "🚩" if is_flagged else " "

  if value == MINE:
    if st.session_state.ms_exploded_pos == (r, c):
      return "💥"
    return "💣"

  if value == 0:
    return "·"

  # 게임 진행 중에는 안개 타일의 숫자를 '?'로 숨겨 주변 숫자로만 연립 추리하도록 유도
  if (r, c) in st.session_state.ms_fog_cells and not st.session_state.ms_game_over:
    return "❓"

  return str(value)


def run():
  """main.py에서 메뉴를 선택했을 때 호출되는 지뢰찾기 메인 실행 함수"""
  init_minesweeper_state()

  st.header("💣 3. 지뢰찾기")
  st.markdown(
      "넓어진 보드와 촘촘한 지뢰밭에서 **모든 안전한 칸**을 열어보세요!\n"
      "- **❓ 안개 타일**: 일부 칸은 숫자가 숨겨지므로 **주변 숫자들을 교차 비교**해 추리해야 합니다.\n"
      "- **⚡ 코드 열기**: 열린 숫자 주변에 숫자만큼 `🚩`을 꽂은 뒤 **그 숫자를 다시 클릭**하면 주변 칸이 한 번에 열립니다. *(오답 깃발이면 즉시 폭발!)*"
  )

  # 1단 컨트롤 바: 난이도 선택 / 남은 지뢰(깃발 한도) / 새 게임 버튼
  col_diff, col_mines, col_reset = st.columns([1.6, 1.4, 1])
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
    flag_count = count_total_flags()
    remaining_mines = st.session_state.ms_mines - flag_count
    st.info(
        f"🚩 남은 깃발: **{remaining_mines}개** / 지뢰 {st.session_state.ms_mines}개 "
        f"(❓안개 {st.session_state.ms_fog_count}칸)"
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
        format_func=lambda x: "🔍 칸 열기 (숫자 클릭 시 코드 열기)"
        if x == "reveal"
        else "🚩 깃발 꽂기 / 해제",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.ms_mode = mode_choice

  with col_hint:
    hint_label = (
        "💡 힌트 사용 완료" if st.session_state.ms_hint_used else "💡 돌파 힌트 (1회)"
    )
    if st.button(
        hint_label,
        disabled=st.session_state.ms_hint_used or st.session_state.ms_game_over,
        use_container_width=True,
    ):
      use_hint()
      st.rerun()

  if st.session_state.ms_flag_warning:
    st.warning("⚠️ 깃발은 총 지뢰 개수만큼만 꽂을 수 있습니다! 기존 깃발을 먼저 해제해 주세요.")

  st.divider()

  # 정사각형 보드판 스타일 적용 및 대형 격자 렌더링
  rows = st.session_state.ms_rows
  cols = st.session_state.ms_cols
  apply_board_style(cols)

  with st.container(key="ms_board_box"):
    for r in range(rows):
      grid_cols = st.columns(cols)
      for c in range(cols):
        with grid_cols[c]:
          label = get_cell_label(r, c)
          chordable = is_chord_ready(r, c)
          is_disabled = st.session_state.ms_game_over or (
              st.session_state.ms_revealed[r][c] and not chordable
          )
          if st.button(
              label,
              key=f"ms_cell_{r}_{c}",
              disabled=is_disabled,
              help="주변 닫힌 칸 한 번에 열기 (코드 열기)" if chordable else None,
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
          "🎉 대단합니다! 안개 타일과 고밀도 지뢰밭을 뚫고 완벽히 클리어했습니다! (JSON 기록 완료)"
      )
    else:
      st.error(
          "💥 지뢰(💥)가 폭발했습니다! 숨겨진 지뢰(💣)와 오답 깃발(❌)을 확인하고 다시 도전해 보세요."
      )


if __name__ == "__main__":
  run()
