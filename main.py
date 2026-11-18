from datetime import datetime  # 현재 접속 시간을 표시하기 위한 기본 모듈
import data_manager as dm  # 모든 모듈이 공통으로 사용하는 JSON 데이터 관리 모듈
import streamlit as st  # 웹 UI 화면 구성을 위한 Streamlit 라이브러리

# 추후 팀원들이 각자 파일에 def run(): 함수를 완성하면 아래 주석을 풀고 연결합니다.
# import game_baseball, game_tictactoe, game_minesweeper, game_updown
# import game_rps, game_relay_math, game_oddeven, game_coin
# import dashboard


def init_session_state():
  """앱 실행 시 game_records.json 파일에서 기존 전적을 불러와 세션에 연결하는 함수"""
  if "game_data" not in st.session_state:
    # JSON 파일이 없으면 자동 생성하고, 있으면 기존 전적을 불러옴
    st.session_state.game_data = dm.load_data()


def render_sidebar(menu_list: list) -> str:
  """왼쪽 사이드바에 닉네임 설정, 메뉴 선택, JSON 기반 전체 전적 요약을 그리는 함수"""
  data = st.session_state.game_data  # 현재 세션에 로드된 JSON 데이터 참조

  with st.sidebar:
    st.title("🎮 Mini-Game Hub")
    st.caption(
        f"접속 시간: {datetime.now().strftime('%H:%M')} | JSON 자동 저장"
    )
    st.divider()

    # 닉네임 변경 시 JSON 파일에도 즉시 업데이트
    name_input = st.text_input("플레이어 닉네임", value=data["player_name"])
    if name_input.strip() and name_input.strip() != data["player_name"]:
      dm.update_player_name(name_input.strip())

    st.divider()
    selected_menu = st.radio("게임 및 메뉴 선택", menu_list)

    st.divider()
    # JSON의 summary 항목에서 8종 게임의 총 플레이 수와 승리 수를 합산
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
  """'🏠 메인 로비' 화면에 JSON에서 불러온 8종 게임별 실시간 전적을 카드로 출력하는 함수"""
  data = st.session_state.game_data
  summary = data["summary"]

  st.title(f"🎉 환영합니다, {data['player_name']}님! 미니게임 아케이드 허브")
  st.markdown(
      "모든 플레이 기록은 **`game_records.json`** 파일에 실시간 저장되어"
      " 통합 대시보드와 공유됩니다."
  )
  st.divider()

  games_info = [
      ("⚾ 숫자 야구 게임", "baseball", "중복 없는 3자리 숫자 추리 게임"),
      ("⭕ 틱택토", "tictactoe", "3x3 보드판 AI 대전 3목 게임"),
      ("💣 지뢰찾기", "minesweeper", "힌트 숫자를 통한 지뢰 탐색 퍼즐"),
      ("🔢 업 앤 다운", "updown", "1~100 사이 숫자를 UP/DOWN 힌트로 맞히기"),
      ("✊ 가위바위보", "rps", "AI와의 가위바위보 심리전 대결"),
      (
          "➕ 릴레이 합 셈하기",
          "relay_math",
          "두 자리 수 덧셈/뺄셈 5문제 스피드 퀴즈",
      ),
      ("🎲 홀짝", "oddeven", "랜덤 숫자의 홀수/짝수 여부를 맞히는 게임"),
      ("🪙 동전 앞뒤", "coin", "동전의 앞면과 뒷면을 예측하는 게임"),
  ]

  for row_start in range(0, len(games_info), 4):
    cols = st.columns(4)
    for idx, (title, key, desc) in enumerate(
        games_info[row_start : row_start + 4]
    ):
      with cols[idx]:
        with st.container(border=True):
          st.subheader(title)
          st.write(desc)
          rec = summary[key]  # JSON에서 해당 게임의 전적 가져오기
          best = (
              f" | 최고: {rec['best_score']}"
              if rec["best_score"] is not None
              else ""
          )
          st.caption(f"전적: {rec['played']}전 {rec['wins']}승{best}")

  st.divider()
  st.info("👈 왼쪽 사이드바 메뉴에서 플레이할 게임을 선택해 주세요!")


def render_placeholder(title: str, filename: str, owner: str):
  """개발 중인 모듈 안내용 임시 화면 함수"""
  st.header(f"🎮 {title}")
  st.warning(
      f"🚧 **[{owner}]** 담당 모듈(`{filename}`)의 `run()` 함수가 연결될"
      " 자리입니다."
  )


def main():
  """프로그램 전체 실행 순서를 제어하는 메인 함수"""
  st.set_page_config(
      page_title="파이썬 미니게임 허브 (8종)", page_icon="🎮", layout="wide"
  )
  init_session_state()

  menus = {
      "🏠 메인 로비": render_home,
      # --- 팀원 1 담당 ---
      "⚾ 숫자 야구 게임": lambda: render_placeholder(
          "숫자 야구 게임", "game_baseball.py", "팀원 1"
      ),
      "⭕ 틱택토": lambda: render_placeholder(
          "틱택토", "game_tictactoe.py", "팀원 1"
      ),
      "💣 지뢰찾기": lambda: render_placeholder(
          "지뢰찾기", "game_minesweeper.py", "팀원 1"
      ),
      "🔢 업 앤 다운": lambda: render_placeholder(
          "업 앤 다운", "game_updown.py", "팀원 1"
      ),
      # --- 팀원 2 담당 ---
      "✊ 가위바위보": lambda: render_placeholder(
          "가위바위보", "game_rps.py", "팀원 2"
      ),
      "➕ 릴레이 합 셈하기": lambda: render_placeholder(
          "릴레이 합 셈하기", "game_relay_math.py", "팀원 2"
      ),
      "🎲 홀짝": lambda: render_placeholder(
          "홀짝", "game_oddeven.py", "팀원 2"
      ),
      "🪙 동전 앞뒤": lambda: render_placeholder(
          "동전 앞뒤", "game_coin.py", "팀원 2"
      ),
      "📊 통합 통계 대시보드": lambda: render_placeholder(
          "통합 통계 대시보드", "dashboard.py", "팀원 2"
      ),
  }

  selected = render_sidebar(list(menus.keys()))
  menus[selected]()


if __name__ == "__main__":
  main()