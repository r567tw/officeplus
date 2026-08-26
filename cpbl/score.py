"""抓取中華職棒大聯盟（CPBL）賽程與比賽比分。

使用方式：
    python cpbl_scores.py
    python cpbl_scores.py --date 2026-08-26
    python cpbl_scores.py --json

資料來源：CPBL 官方賽程頁面的 getgamedatas API。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from typing import Any

import requests

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
    print(game)
    if result == "" and value(game, "GameDateTimeE"):
        status = "已結束"
    if result == "" and value(game, "IsPlayBall") == "N":
        status = "未開賽"
    if result == "" and value(game, "IsPlayBall") == "Y":
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


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 CPBL 官方賽程與比賽比分")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="查詢日期，格式 YYYY-MM-DD（預設今天）",
    )
    parser.add_argument("--location", default="", help="球場篩選，預設全部")
    parser.add_argument("--kind-code", default="A", help="賽事類別代碼，預設 A")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式輸出")
    args = parser.parse_args()

    try:
        games = fetch_games(args.date, args.location, args.kind_code)
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"抓取失敗：{exc}", file=sys.stderr)
        return 1

    output = [simplify_game(game) for game in games]
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    print(f"CPBL {args.date} 比賽：{len(output)} 場")
    if not output:
        print("當天沒有比賽資料。")
        return 0

    for game in output:
        print(
            f"{game['時間']} | {game['客隊']} {game['客隊比分']} - "
            f"{game['主隊']} {game['主隊比分']} | {game['狀態']} | "
            f"{game['球場']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
