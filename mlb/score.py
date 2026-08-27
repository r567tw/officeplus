"""抓取 MLB 賽程與比賽比分。

使用方式：
    python MLB_Score.py
    python MLB_Score.py --date 2026-08-26
    python MLB_Score.py --json

資料來源：MLB Stats API（公開使用，不需要 API key）。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
DEFAULT_TIMEOUT = 20
TAIPEI_TIMEZONE = timezone(timedelta(hours=8), "Taipei")


def fetch_games(target_date: str) -> list[dict[str, Any]]:
    """取得指定日期的 MLB 比賽資料。日期格式為 YYYY-MM-DD。"""
    response = requests.get(
        SCHEDULE_URL,
        params={
            "sportId": 1,
            "date": target_date,
            "hydrate": "venue,team,linescore",
        },
        headers={"User-Agent": "mlb-scores/1.0"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    games: list[dict[str, Any]] = []
    for schedule_date in payload.get("dates", []):
        games.extend(schedule_date.get("games", []))
    return games


def team_name(game: dict[str, Any], side: str) -> str:
    """取得客隊或主隊名稱。"""
    return str(game.get("teams", {}).get(side, {}).get("team", {}).get("name", ""))


def team_score(game: dict[str, Any], side: str) -> str:
    """取得客隊或主隊比分，未開賽時以 - 表示。"""
    score = game.get("teams", {}).get(side, {}).get("score")
    return str(score) if score is not None else "-"


def game_time(game: dict[str, Any]) -> str:
    """將 MLB API 的 UTC 比賽時間轉成台北時間。"""
    raw_time = str(game.get("gameDate", ""))
    if not raw_time:
        return ""
    parsed_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    return parsed_time.astimezone(TAIPEI_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S Taipei")


def inning_status(game: dict[str, Any]) -> str:
    """取得目前進行局數與上下半局，保留 MLB API 英文格式。"""
    game_status = game.get("status", {}).get("abstractGameState")
    if game_status == "Preview":
        return "Not started"
    if game_status == "Final":
        return "Final"

    linescore = game.get("linescore", {})
    ordinal = linescore.get("currentInningOrdinal")
    if not ordinal:
        return "Unknown"
    half = "Top" if linescore.get("isTopInning") else "Bottom"
    return f"{ordinal} {half}"


def simplify_game(game: dict[str, Any]) -> dict[str, str]:
    """將 MLB 比賽物件整理成適合顯示或存檔的欄位。"""
    status = game.get("status", {})
    return {
        "比賽編號": str(game.get("gamePk", "")),
        "時間": game_time(game),
        "客隊": team_name(game, "away"),
        "主隊": team_name(game, "home"),
        "客隊比分": team_score(game, "away"),
        "主隊比分": team_score(game, "home"),
        "球場": str(game.get("venue", {}).get("name", "")),
        "局數": inning_status(game),
        "狀態": str(status.get("detailedState", status.get("abstractGameState", "未知"))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 MLB 官方賽程與比賽比分")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="查詢日期，格式 YYYY-MM-DD（預設今天）",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 格式輸出")
    args = parser.parse_args()

    try:
        games = fetch_games(args.date)
    except (requests.RequestException, ValueError) as exc:
        print(f"抓取失敗：{exc}", file=sys.stderr)
        return 1

    output = [simplify_game(game) for game in games]
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    print(f"MLB {args.date} 比賽：{len(output)} 場")
    if not output:
        print("當天沒有比賽資料。")
        return 0

    for game in output:
        print(
            f"{game['時間']} | {game['客隊']} {game['客隊比分']} - "
            f"{game['主隊']} {game['主隊比分']} | {game['局數']} | {game['狀態']} | "
            f"{game['球場']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())