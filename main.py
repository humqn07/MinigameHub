from datetime import datetime  # 현재 접속 시간을 표시하기 위한 파이썬 기본 모듈
import importlib  # 문자열 이름만으로 모듈을 동적으로 불러오기 위한 파이썬 기본 모듈
import data_manager as dm  # 모든 모듈이 공통으로 사용하는 JSON 데이터 관리 모듈
import streamlit as st  # 웹 UI 화면 구성을 위한 Streamlit 라이브러리


def is_module_ready(module_name: str) -> bool:
  """모듈 파일이 존재하고, 그 안에 실행 가능한 run() 함수까지 구현되어 있는지 확인하는 함수"""
  try:
    module = importlib.import_module(module_name)  # 모듈 파일 불러오기 시도
    importlib.reload(module)  # 수정된 최신 코드 반영을 위해 새로고침
    # 파일이 비어있지 않고 내부에 'run'이라는 호출 가능한 함수가 있는지 검사
    return hasattr(module, "run") and callable(getattr(module, "run"))
  except Exception:
    # 파일이 아예 없거나(ModuleNotFoundError), 작성 중 문법 오류가 있어도 프로그램이 멈추지 않게 False 반환
    return False


def load_module_runner(module_name: str, title: str):
  """
    모듈 파일과 run() 함수가 모두 준비되었으면 실제 게임의 run() 함수를 반환하고,
    파일이 없거나 빈 파일이면 에러 대신 임시 안내 화면 함수를 반환하는 안전 연결 함수
    """
  if is_module_ready(module_name):
    module = importlib.import_module(module_name)
    return module.run  # 정상 구현된 모듈의 run() 함수 반환
  else:
    # 파일이 없거나 비어 있는 경우 임시 안내 화면 함수 반환
    return lambda: render_placeholder(title, f"{module_name}.py")


def init_session_state():
  """프로그램 실행 시 JSON 전적 데이터와 현재 선택된 화면 상태를 세션에 초기화하는 함수"""
  if "game_data" not in st.session_state:
    # JSON 파일이 없으면 기본 구조로 자동 생성하고, 있으면 기존 전적을 불러옴
    st.session_state.game_data = dm.load_data()

  # 현재 보고 있는 화면 메뉴 상태 (기본값: 메인 로비)
  if "current_menu" not in st.session_state:
    st.session_state.current_menu = "🏠 메인 로비"


def navigate_to(menu_name: str):
  """메인 화면에서 선택한 게임 또는 로비로 화면을 전환하는 함수"""
  st.session_state.current_menu = menu_name
  st.rerun()


def render_sidebar():
  """왼쪽 사이드바에 닉네임 입력창, 요약 전적, 홈/대시보드 바로가기를 그리는 함수"""
  data = st.session_state.game_data  # 현재 세션에 로드된 JSON 데이터

  with st.sidebar:
    st.title("🎮 Mini-Game Hub")
    st.caption(
        f"접속 시간: {datetime.now().strftime('%H:%M')} | JSON 자동 저장"
    )
    st.divider()

    # 플레이어 닉네임 입력 및 JSON 즉시 동기화
    name_input = st.text_input("플레이어 닉네임", value=data["player_name"])
    if name_input.strip() and name_input.strip() != data["player_name"]:
      dm.update_player_name(name_input.strip())

    st.divider()
    # 8종 게임의 전체 플레이 횟수, 승리 횟수, 종합 승률 계산
    summary = data["summary"]
    total_played = sum(g["played"] for g in summary.values())
    total_wins = sum(g["wins"] for g in summary.values())
    win_rate = (total_wins / total_played * 100) if total_played > 0 else 0.0

    st.info(
        f"👤 **{data['player_name']}**님\n\n"
        f"총 플레이: **{total_played}회** | 종합 승률: **{win_rate:.1f}%**"
    )

    st.divider()
    # 사이드바에서는 게임 라디오 목록 대신 로비·대시보드 빠른 이동 버튼만 제공
    if st.button("🏠 메인 로비", use_container_width=True):
      navigate_to("🏠 메인 로비")
    if st.button("📊 통합 통계 대시보드", use_container_width=True):
      navigate_to("📊 통합 통계 대시보드")


def render_home():
  """'🏠 메인 로비' 화면에 8종 게임 카드를 출력하고 클릭 시 해당 게임을 바로 실행하는 함수"""
  data = st.session_state.game_data
  summary = data["summary"]

  col_title, col_dash = st.columns([3.5, 1])
  with col_title:
    st.title(f"🎉 환영합니다, {data['player_name']}님! 미니게임 아케이드 허브")
    st.markdown(
        "플레이할 게임을 아래 목록에서 **직접 클릭**해 바로 시작해 보세요! "
        "(모든 기록은 **`game_records.json`**에 자동 저장됩니다)"
    )
  with col_dash:
    st.write("")
    if st.button("📊 통합 통계 대시보드 보기", use_container_width=True):
      navigate_to("📊 통합 통계 대시보드")

  st.divider()

  # 8종 게임 정보 (화면 제목, 세션 키, 모듈 파일명, 한 줄 설명)
  games_info = [
      (
          "⚾ 숫자 야구 게임",
          "baseball",
          "game_baseball",
          "중복 없는 3자리 숫자 추리 게임",
      ),
      ("⭕ 틱택토", "tictactoe", "game_tictactoe", "3x3 보드판 AI 대전 3목 게임"),
      (
          "💣 지뢰찾기",
          "minesweeper",
          "game_minesweeper",
          "힌트 숫자를 통한 지뢰 탐색 퍼즐",
      ),
      (
          "🔢 업 앤 다운",
          "updown",
          "game_updown",
          "1~100 사이 숫자를 UP/DOWN 힌트로 맞히기",
      ),
      ("✊ 가위바위보", "rps", "game_rps", "AI와의 가위바위보 심리전 대결"),
      (
          "➕ 주사위 합 연속 맞추기",
          "relay_math",
          "game_relay_math",
          "제한 시간 안에 주사위 눈 합계 연속 맞히기",
      ),
      (
          "🎲 홀짝 맞추기",
          "oddeven",
          "game_oddeven",
          "랜덤 숫자의 홀수/짝수 여부를 맞히는 게임",
      ),
      ("🪙 동전 던지기", "coin", "game_coin", "동전의 앞면과 뒷면을 예측하는 게임"),
  ]

  # 4열 x 2행 그리드 카드 레이아웃으로 출력 (카드 내 버튼 클릭 시 즉시 게임 실행)
  for row_start in range(0, len(games_info), 4):
    cols = st.columns(4)
    for idx, (title, key, mod_name, desc) in enumerate(
        games_info[row_start : row_start + 4]
    ):
      with cols[idx]:
        with st.container(border=True):
          st.subheader(title)
          st.write(desc)

          # 실제 run() 함수까지 구현되었는지 확인해 상태 표시
          ready = is_module_ready(mod_name)
          st.caption("✅ 플레이 가능" if ready else "🚧 준비 중")

          # JSON에 기록된 전적 및 최고 기록 표시
          rec = summary[key]
          best = (
              f" | 최고: {rec['best_score']}"
              if rec["best_score"] is not None
              else ""
          )
          st.caption(f"전적: {rec['played']}전 {rec['wins']}승{best}")

          # 메인 화면 카드에서 바로 게임을 실행하는 버튼
          btn_label = "▶️ 게임 시작" if ready else "🚧 준비 중"
          btn_type = "primary" if ready else "secondary"
          if st.button(
              btn_label,
              key=f"launch_{key}",
              type=btn_type,
              use_container_width=True,
          ):
            navigate_to(title)

  # 로비 하단에 최근 플레이 기록 미니 피드(최근 5판) 출력
  render_recent_logs(data.get("logs", []), games_info)


def render_recent_logs(logs: list, games_info: list, limit: int = 5):
  """로비 하단에 최근 플레이 기록(최대 limit건)을 요약 표로 출력하는 함수"""
  st.divider()
  st.subheader(f"🕒 최근 플레이 기록 (최근 {limit}판)")

  # 아직 플레이 기록이 한 건도 없는 경우 안내 문구만 출력
  if not logs:
    st.caption("아직 플레이 기록이 없습니다. 위의 게임 카드를 눌러 첫 판을 시작해 보세요!")
    return

  # 게임 키(예: "baseball")를 화면 표시용 제목(예: "⚾ 숫자 야구 게임")으로 바꾸기 위한 딕셔너리 생성
  game_title_map = {key: title for title, key, _, _ in games_info}

  # 전체 로그 중 가장 최근 limit건을 꺼내 최신순(역순)으로 정렬
  recent_logs = logs[-limit:][::-1]

  # 표(st.table)에 출력할 행 리스트 구성
  display_rows = []
  for entry in recent_logs:
    game_key = entry.get("game", "")  # 저장된 게임 키
    game_label = game_title_map.get(game_key, game_key)  # 매핑된 한글 게임명
    result_raw = entry.get("result", "")  # "WIN" 또는 "LOSE"
    result_label = "🏆 승리" if result_raw == "WIN" else "💥 패배"  # 보기 쉬운 결과 배지
    score_val = entry.get("score")  # 점수/시도횟수/연승 등 (없으면 None)
    score_label = str(score_val) if score_val is not None else "-"

    display_rows.append({
        "플레이 시각": entry.get("timestamp", "-"),
        "플레이어": entry.get("player", "-"),
        "게임": game_label,
        "결과": result_label,
        "기록": score_label,
    })

  st.table(display_rows)  # 최근 플레이 기록 요약 표 출력

  # 전체 기록이 limit건보다 많으면 대시보드 안내 문구 표시
  if len(logs) > limit:
    st.caption(
        f"전체 {len(logs)}판 중 최근 {limit}판만 표시 중입니다. "
        "전체 기록은 '📊 통합 통계 대시보드'에서 확인할 수 있습니다."
    )


def render_placeholder(title: str, filename: str):
  """아직 구현되지 않은 모듈을 선택했을 때 안내 메시지를 띄우는 임시 화면 함수"""
  st.header(f"🎮 {title}")
  st.warning(f"🚧 `{filename}` 모듈이 아직 구현되지 않았습니다.")
  st.info(
      f"💡 같은 폴더에 `{filename}` 파일을 만들고 안에 `def run():` 함수를"
      " 작성하면 자동으로 연결됩니다!"
  )


def main():
  """프로그램의 전체 실행 순서를 제어하는 메인 진입점 함수"""
  # 1. 웹 브라우저 탭 제목 및 와이드 화면 설정
  st.set_page_config(
      page_title="파이썬 미니게임 허브 (8종)", page_icon="🎮", layout="wide"
  )

  # 2. JSON 전적 데이터 및 현재 화면 상태 초기화
  init_session_state()

  # 3. 전체 화면과 모듈 자동 연결 매핑 (파일이 구현되면 자동으로 run() 함수가 연결됨)
  menus = {
      "🏠 메인 로비": render_home,
      "⚾ 숫자 야구 게임": load_module_runner("game_baseball", "숫자 야구 게임"),
      "⭕ 틱택토": load_module_runner("game_tictactoe", "틱택토"),
      "💣 지뢰찾기": load_module_runner("game_minesweeper", "지뢰찾기"),
      "🔢 업 앤 다운": load_module_runner("game_updown", "업 앤 다운"),
      "✊ 가위바위보": load_module_runner("game_rps", "가위바위보"),
      "➕ 주사위 합 연속 맞추기": load_module_runner(
          "game_relay_math", "주사위 합 연속 맞추기"
      ),
      "🎲 홀짝 맞추기": load_module_runner("game_oddeven", "홀짝 맞추기"),
      "🪙 동전 던지기": load_module_runner("game_coin", "동전 던지기"),
      "📊 통합 통계 대시보드": load_module_runner(
          "dashboard", "통합 통계 대시보드"
      ),
  }

  # 4. 사이드바(닉네임·요약 전적) 렌더링
  render_sidebar()

  # 5. 게임이나 대시보드 화면에 들어와 있을 때는 상단에 '메인 로비로 돌아가기' 버튼 표시
  current = st.session_state.current_menu
  if current not in menus:
    current = "🏠 메인 로비"
    st.session_state.current_menu = current

  if current != "🏠 메인 로비":
    col_back, _ = st.columns([1.2, 4.8])
    with col_back:
      if st.button("⬅️ 메인 로비로 돌아가기", use_container_width=True):
        navigate_to("🏠 메인 로비")
    st.divider()

  # 6. 현재 선택된 화면 실행
  menus[current]()


if __name__ == "__main__":
  main()