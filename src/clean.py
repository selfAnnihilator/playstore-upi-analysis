"""Clean raw review parquet files and load them into SQLite (data/reviews.db, table `reviews`)."""
import re
import sqlite3

import pandas as pd
from langdetect import DetectorFactory, LangDetectException, detect

from config import DB_PATH, RAW_DIR

DetectorFactory.seed = 0
MIN_WORDS = 3  # shorter reviews ("good", "nice app") are kept for rating stats but not theme-tagged


def is_english(text: str) -> bool:
    # Hinglish ("paisa nahi aaya") is common; langdetect labels it variously, so only
    # trust it for longer texts and treat pure-ASCII short texts as English.
    if len(text) < 40:
        return text.isascii()
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False


def major_version(v) -> str | None:
    if not isinstance(v, str):
        return None
    m = re.match(r"(\d+)\.(\d+)", v)
    return f"{m.group(1)}.{m.group(2)}" if m else None


def main() -> None:
    frames = [pd.read_parquet(p) for p in sorted(RAW_DIR.glob("*.parquet"))]
    df = pd.concat(frames, ignore_index=True)
    n0 = len(df)

    df = df.drop_duplicates("reviewId")
    df["content"] = df["content"].fillna("").str.strip()
    df["word_count"] = df["content"].str.split().str.len()
    df = df[df["content"] != ""].copy()
    df["is_english"] = df["content"].map(is_english)

    df["at"] = pd.to_datetime(df["at"])
    df["repliedAt"] = pd.to_datetime(df["repliedAt"])
    df["review_date"] = df["at"].dt.strftime("%Y-%m-%d")
    df["month"] = df["at"].dt.strftime("%Y-%m")
    df["week"] = df["at"].dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    # High-volume apps reach 30k reviews in days, low-volume ones in months. Cross-app
    # comparisons use only the window all apps cover: from the first full day after the
    # latest per-app start date.
    common_start = (df.groupby("app")["at"].min().max().normalize() + pd.Timedelta(days=1))
    df["in_common_window"] = (df["at"] >= common_start).astype(int)
    df["version_major"] = df["appVersion"].map(major_version)
    df["has_reply"] = df["replyContent"].notna().astype(int)
    df["reply_hours"] = ((df["repliedAt"] - df["at"]).dt.total_seconds() / 3600).round(1)

    out = df.rename(columns={
        "reviewId": "review_id", "score": "rating", "thumbsUpCount": "thumbs_up",
        "appVersion": "app_version", "replyContent": "reply_content",
    })[[
        "review_id", "app", "rating", "content", "word_count", "is_english", "thumbs_up",
        "app_version", "version_major", "review_date", "month", "week", "in_common_window", "has_reply", "reply_hours", "reply_content",
    ]]

    with sqlite3.connect(DB_PATH) as con:
        out.to_sql("reviews", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_reviews_app_month ON reviews(app, month)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_reviews_id ON reviews(review_id)")
    print(f"common window starts {common_start.date()}")
    print(f"raw {n0} -> cleaned {len(out)} rows ({out['is_english'].mean():.0%} English) -> {DB_PATH.name}")
    print(out.groupby("app").size().to_string())


if __name__ == "__main__":
    main()
