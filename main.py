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
  """프로그램 실행 시 game_records.json 파일을 불러와 세션에 연결하는 함수"""
  if "game_data" not in st.session_state:
    # JSON 파일이 없으면 기본 구조로 자동 생성하고, 있으면 기존 전적을 불러옴
    st.session_state.game_data = dm.load_data()


def render_sidebar(menu_list: list) -> str:
  """왼쪽 사이드바에 닉네임 입력창, 메뉴 선택 버튼, JSON 기반 요약 전적을 그리는 함수"""
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
    # 메뉴 리스트를 라디오 버튼으로 출력하고 선택된 메뉴 이름 반환
    selected_menu = st.radio("게임 및 메뉴 선택", menu_list)

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

  return selected_menu


def render_home():
  """'🏠 메인 로비' 화면에 8종 게임 카드 목록과 모듈 구현 상태, 실시간 전적을 출력하는 함수"""
  data = st.session_state.game_data
  summary = data["summary"]

  st.title(f"🎉 환영합니다, {data['player_name']}님! 미니게임 아케이드 허브")
  st.markdown(
      "모든 플레이 기록은 **`game_records.json`** 파일에 실시간 저장되어"
      " 통합 대시보드와 공유됩니다."
  )
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
          "➕ 릴레이 합 셈하기",
          "relay_math",
          "game_relay_math",
          "두 자리 수 덧셈/뺄셈 5문제 스피드 퀴즈",
      ),
      (
          "🎲 홀짝",
          "oddeven",
          "game_oddeven",
          "랜덤 숫자의 홀수/짝수 여부를 맞히는 게임",
      ),
      ("🪙 동전 앞뒤", "coin", "game_coin", "동전의 앞면과 뒷면을 예측하는 게임"),
  ]

  # 4열 x 2행 그리드 카드 레이아웃으로 출력
  for row_start in range(0, len(games_info), 4):
    cols = st.columns(4)
    for idx, (title, key, mod_name, desc) in enumerate(
        games_info[row_start : row_start + 4]
    ):
      with cols[idx]:
        with st.container(border=True):
          st.subheader(title)
          st.write(desc)

          # 해당 모듈 파일이 이미 구현되었는지 확인해 상태 배지 표시
          try:
            importlib.import_module(mod_name)
            st.caption("✅ 플레이 가능")
          except ModuleNotFoundError:
            st.caption("🚧 준비 중")

          # JSON에 기록된 전적 및 최고 기록 표시
          rec = summary[key]
          best = (
              f" | 최고: {rec['best_score']}"
              if rec["best_score"] is not None
              else ""
          )
          st.caption(f"전적: {rec['played']}전 {rec['wins']}승{best}")

  st.divider()
  st.info("👈 왼쪽 사이드바 메뉴에서 플레이할 게임을 선택해 주세요!")


def render_placeholder(title: str, filename: str):
  """아직 파일이 생성되지 않은 모듈을 선택했을 때 안내 메시지를 띄우는 임시 화면 함수"""
  st.header(f"🎮 {title}")
  st.warning(f"🚧 `{filename}` 모듈이 아직 생성되지 않았습니다.")
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

  # 2. JSON 전적 데이터 초기화 및 로드
  init_session_state()

  # 3. 전체 메뉴와 모듈 자동 연결 매핑 (파일이 생기면 자동으로 run() 함수가 연결됨)
  menus = {
      "🏠 메인 로비": render_home,
      "⚾ 숫자 야구 게임": load_module_runner("game_baseball", "숫자 야구 게임"),
      "⭕ 틱택토": load_module_runner("game_tictactoe", "틱택토"),
      "💣 지뢰찾기": load_module_runner("game_minesweeper", "지뢰찾기"),
      "🔢 업 앤 다운": load_module_runner("game_updown", "업 앤 다운"),
      "✊ 가위바위보": load_module_runner("game_rps", "가위바위보"),
      "➕ 릴레이 합 셈하기": load_module_runner(
          "game_relay_math", "릴레이 합 셈하기"
      ),
      "🎲 홀짝": load_module_runner("game_oddeven", "홀짝"),
      "🪙 동전 앞뒤": load_module_runner("game_coin", "동전 앞뒤"),
      "📊 통합 통계 대시보드": load_module_runner(
          "dashboard", "통합 통계 대시보드"
      ),
  }

  # 4. 사이드바 렌더링 및 사용자 메뉴 선택 받기
  selected = render_sidebar(list(menus.keys()))

  # 5. 선택된 메뉴에 연결된 함수 실행
  menus[selected]()


if __name__ == "__main__":
  main()
