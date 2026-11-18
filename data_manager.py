from datetime import datetime  # 게임 종료 시각을 기록하기 위한 기본 모듈
import json  # JSON 파일 읽기/쓰기를 위한 파이썬 기본 모듈
import os  # JSON 파일이 폴더에 존재하는지 확인하기 위한 기본 모듈
import streamlit as st  # 세션 상태와 JSON 데이터를 동기화하기 위한 라이브러리

JSON_FILE_PATH = "game_records.json"  # 모든 모듈이 공통으로 사용할 JSON 파일 이름

# 8종 게임의 표준 키(Key) 목록 (오타 방지용)
GAME_KEYS = [
    "baseball",  # 1. 숫자 야구 게임
    "tictactoe",  # 2. 틱택토
    "minesweeper",  # 3. 지뢰찾기
    "updown",  # 4. 업 앤 다운
    "rps",  # 5. 가위바위보
    "relay_math",  # 6. 릴레이 합 셈하기
    "oddeven",  # 7. 홀짝
    "coin",  # 8. 동전 앞뒤
]


def get_default_data() -> dict:
  """JSON 파일이 처음 생성될 때 사용할 기본 딕셔너리 구조를 반환하는 함수"""
  return {
      "player_name": "Player 1",  # 기본 플레이어 닉네임
      # 8종 게임별 요약 전적 (플레이 수, 승리 수, 최고 기록)
      "summary": {
          key: {"played": 0, "wins": 0, "best_score": None} for key in GAME_KEYS
      },
      # 모든 게임의 개별 플레이 기록이 시간순으로 쌓이는 리스트 (대시보드 차트용)
      "logs": [],
  }


def load_data() -> dict:
  """game_records.json 파일을 읽어와 딕셔너리로 반환하는 함수 (파일이 없으면 자동 생성)"""
  if not os.path.exists(JSON_FILE_PATH):  # 폴더에 JSON 파일이 아직 없는 경우
    default_data = get_default_data()  # 기본 데이터 구조 생성
    save_data(default_data)  # 새 JSON 파일로 즉시 저장
    return default_data

  # 한글 깨짐 방지를 위해 utf-8 인코딩으로 JSON 파일 열기
  with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
    return json.load(f)


def save_data(data: dict):
  """전달받은 딕셔너리 데이터를 game_records.json 파일에 예쁘게(indent=4) 저장하는 함수"""
  with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
    # ensure_ascii=False: 한글 닉네임이나 게임명이 유니코드(\uXXXX)로 깨지지 않고 한글 그대로 저장됨
    json.dump(data, f, ensure_ascii=False, indent=4)


def update_player_name(new_name: str):
  """플레이어 닉네임이 변경되었을 때 세션과 JSON 파일에 동시에 반영하는 함수"""
  data = load_data()  # 현재 JSON 데이터 불러오기
  data["player_name"] = new_name  # 닉네임 수정
  save_data(data)  # JSON 파일에 저장
  st.session_state.game_data = data  # 현재 화면 세션에도 즉시 반영


def record_game_result(
    game_key: str,
    is_win: bool,
    score: float = None,
    lower_is_better: bool = True,
):
  """
    [핵심 공용 함수] 각 게임이 끝날 때 호출하면 요약 전적(summary)과 상세 로그(logs)를 JSON에 자동 저장함
    - game_key: 게임 고유 키 (예: "baseball", "relay_math" 등)
    - is_win: 승리 여부 (True 또는 False)
    - score: 이번 판의 성과 수치 (예: 숫자야구 시도 횟수 5, 릴레이 암산 걸린 시간 12.4초 등 / 없으면 None)
    - lower_is_better: 최고 기록 갱신 기준 (True면 낮을수록 최고 기록[시도횟수·시간], False면 높을수록 최고 기록[연승·점수])
    """
  data = load_data()  # 최신 JSON 데이터 불러오기
  game_stat = data["summary"][game_key]  # 해당 게임의 요약 전적 딕셔너리 선택

  # 1. 플레이 횟수 및 승리 횟수 누적
  game_stat["played"] += 1
  if is_win:
    game_stat["wins"] += 1

    # 2. 승리했을 때 점수(score)가 있다면 최고 기록(best_score) 갱신 여부 확인
    if score is not None:
      current_best = game_stat["best_score"]
      if current_best is None:  # 첫 승리 기록이면 무조건 최고 기록으로 등록
        game_stat["best_score"] = score
      elif (
          lower_is_better and score < current_best
      ):  # 시도 횟수·시간 등 낮을수록 좋은 경우
        game_stat["best_score"] = score
      elif (
          not lower_is_better and score > current_best
      ):  # 콤보·점수 등 높을수록 좋은 경우
        game_stat["best_score"] = score

  # 3. 대시보드 추이 그래프를 위한 상세 플레이 로그 추가
  data["logs"].append({
      "timestamp": datetime.now().strftime(
          "%Y-%m-%d %H:%M:%S"
      ),  # 게임 종료 시간
      "player": data["player_name"],  # 플레이어 이름
      "game": game_key,  # 게임 종류
      "result": "WIN" if is_win else "LOSE",  # 승패 결과
      "score": score,  # 기록 점수
  })

  # 4. 변경된 전체 데이터를 JSON 파일과 세션 상태에 동시 저장
  save_data(data)
  st.session_state.game_data = data