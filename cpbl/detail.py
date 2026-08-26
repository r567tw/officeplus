
import requests
import sys
import re
import json
from typing import Any

BASE_URL = "https://www.cpbl.com.tw"
SCHEDULE_URL = f"{BASE_URL}/schedule"
GAME_DATA_URL = f"{BASE_URL}/schedule/getgamedatas"
DEFAULT_TIMEOUT = 20

def get_verification_token(session: requests.Session) -> str:
    """從官方賽程頁取得 API 所需的 RequestVerificationToken。"""
    response = session.get(SCHEDULE_URL, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()

    endpoint_start = response.text.find("/schedule/getgamedatas")
    if endpoint_start == -1:
        raise RuntimeError("找不到官方 API 驗證 token，可能是網站格式已變更。")

    endpoint_block = response.text[endpoint_start : endpoint_start + 5000]
    match = re.search(
        r"RequestVerificationToken:\s*['\"]([^'\"]+)['\"]",
        endpoint_block,
    )
    if not match:
        raise RuntimeError("官方 API 驗證 token 格式無法解析。")

    return match.group(1)

def fetch_games(target_date: str, location: str = "", kind_code: str = "A") -> list[dict[str, Any]]:
    """取得指定日期所在年度的比賽資料。日期格式為 YYYY-MM-DD。"""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "cpbl-scores/1.0 (+https://www.cpbl.com.tw/)",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
    )
    token = get_verification_token(session)

    year = target_date[:4]
    response = session.post(
        GAME_DATA_URL,
        data={
            "calendar": f"{year}/01/01",
            "location": location,
            "kindCode": kind_code,
        },
        headers={
            "RequestVerificationToken": token,
            "Referer": SCHEDULE_URL,
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("Success"):
        raise RuntimeError(f"CPBL API 回傳失敗：{payload}")

    raw_games = payload.get("GameDatas", "[]")
    games = json.loads(raw_games) if isinstance(raw_games, str) else raw_games
    return [game for game in games if str(game.get("GameDate", "")).startswith(target_date)]


def value(game: dict[str, Any], *names: str, default: str = "") -> str:
    """從官方欄位中取第一個非空值，兼容欄位小幅改名。"""
    for name in names:
        item = game.get(name)
        if item is not None and str(item).strip():
            return str(item).strip()
    return default

def game_detail(game: dict[str, Any]) -> dict[str, Any]:
    """取得比賽詳細資訊。"""
    game_id = value(game, "GameSno", "GameNo")
    if not game_id:
        raise ValueError("無法取得比賽編號。")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "cpbl-scores/1.0 (+https://www.cpbl.com.tw/)",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
    )
    token = get_verification_token(session)

    response = session.post(
        f"{BASE_URL}/home/gamedetail",
        data={"GameSno": game_id, "Year": "2026", "KindCode": "A"},
        headers={
            "RequestVerificationToken": token,
            "Referer": SCHEDULE_URL,
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    # print(response.text)  # Debug: Print the payload to see its structure
    if not payload.get("Success"):
        raise RuntimeError(f"CPBL API 回傳失敗：{payload}")

    return payload.get("GameDetail", {})

def simplify_game(game: dict[str, Any]) -> dict[str, str]:
    """將官方比賽物件整理成適合顯示或存檔的欄位。"""
    result = value(game, "GameResult")
    status = {
        "": "未開賽／進行中",
        "0": "已結束",
        "1": "延賽",
        "2": "保留",
        "4": "取消",
    }.get(result, f"未知狀態（{result}）")
    if result == "" and game["GameDateTimeE"] != None:
        status = "已結束"
    if result == "" and game["IsPlayBall"] == "N":
        status = "未開賽"
    if result == "" and game["IsPlayBall"] == "Y":
        status = "進行中"

    return {
        "比賽編號": value(game, "GameSno", "GameNo"),
        "時間": value(game, "PreExeDate", "GameDateTimeS"),
        "客隊": value(game, "VisitingTeamName", "VisitingTeam"),
        "主隊": value(game, "HomeTeamName", "HomeTeam"),
        "客隊比分": value(game, "VisitingScore", "VisitingTeamScore", default="-"),
        "主隊比分": value(game, "HomeScore", "HomeTeamScore", default="-"),
        "球場": value(game, "FieldAbbe", "FieldName"),
        "狀態": status,
    }

try:
    games = fetch_games('2026-08-26', "", "A")
    for game in games:
        simplified = simplify_game(game)
        detail = game_detail(game)
        print(detail)
        break  # 只抓第一場比賽的詳細資訊
except (requests.RequestException, ValueError, RuntimeError) as exc:
    print(f"抓取失敗：{exc}", file=sys.stderr)
