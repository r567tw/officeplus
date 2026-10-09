"""列出 Google 新聞台灣最新 RSS 的前十則新聞。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import sys
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


SEARCH_QUERY = (
    "台灣 (科技 OR 科學 OR 經濟 OR 產業 "
    "OR 教育 OR 公共政策) when:7d"
)
FEED_URL = "https://news.google.com/rss/search?" + urlencode(
    {
        "q": SEARCH_QUERY,
        "hl": "zh-TW",
        "gl": "TW",
        "ceid": "TW:zh-Hant",
    }
)
EXCLUDED_SOURCES = ("yahoo",)


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    published_at: datetime | None
    source: str


def fetch_news(limit: int = 10) -> list[NewsItem]:
    if limit < 1:
        raise ValueError("新聞則數必須至少為 1。")

    request = Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=15) as response:
        feed_data = response.read()

    root = ET.fromstring(feed_data)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS 內容缺少 channel，無法讀取新聞。")

    news: list[NewsItem] = []
    for entry in channel.findall("item"):
        title = (entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        if not title or not link:
            continue

        published_at = None
        pub_date = entry.findtext("pubDate")
        if pub_date:
            try:
                published_at = parsedate_to_datetime(pub_date)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                pass

        source = (entry.findtext("source") or "").strip()
        if any(excluded in source.casefold() for excluded in EXCLUDED_SOURCES):
            continue
        news.append(NewsItem(title, link, published_at, source))

    if not news:
        raise ValueError("RSS 中沒有可顯示的新聞。")

    oldest = datetime.min.replace(tzinfo=timezone.utc)
    news.sort(key=lambda item: item.published_at or oldest, reverse=True)
    return news[:limit]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        news = fetch_news()
    except (URLError, TimeoutError, ET.ParseError, ValueError) as error:
        print(f"讀取新聞失敗：{error}", file=sys.stderr)
        return 1

    # print("台灣實用新聞：科技、科學、經濟、健康、教育、環境與公共政策")
    # print("（近 7 天，依發布時間排序；已排除 Yahoo）\n")
    for number, item in enumerate(news, start=1):
        number_format = f"{number:02d}"
        if item.published_at is None:
            published = "時間未提供"
        else:
            published = item.published_at.astimezone().strftime("%Y-%m-%d %H:%M")
        print(f"{number_format}. {item.title} | {published} | {item.link}")


    return 0


if __name__ == "__main__":
    raise SystemExit(main())

