"""Scrape recent English Play Store reviews (India) for the three largest UPI apps.

Writes one parquet file per app to data/raw/. Personal fields (user name, avatar)
are dropped at source and never stored.
"""
import time

import pandas as pd
from google_play_scraper import Sort, reviews

from config import APPS, BATCH_SIZE, RAW_DIR, REVIEWS_PER_APP

KEEP = ["reviewId", "score", "content", "thumbsUpCount", "appVersion", "at", "replyContent", "repliedAt"]


def fetch(app_id: str, target: int) -> list[dict]:
    rows, token, retries = [], None, 0
    while len(rows) < target:
        try:
            batch, token = reviews(
                app_id, lang="en", country="in", sort=Sort.NEWEST,
                count=min(BATCH_SIZE, target - len(rows)), continuation_token=token,
            )
        except Exception as exc:  # network hiccups / throttling
            retries += 1
            if retries > 5:
                print(f"  giving up after {len(rows)} rows: {exc}")
                break
            time.sleep(2 * retries)
            continue
        retries = 0
        if not batch:
            break
        rows.extend({k: r.get(k) for k in KEEP} for r in batch)
        if len(rows) % 2000 < BATCH_SIZE:
            print(f"  {len(rows):>6} rows")
        if token is None or token.token is None:
            break
        time.sleep(0.3)
    return rows


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, app_id in APPS.items():
        print(f"Scraping {name} ({app_id})")
        df = pd.DataFrame(fetch(app_id, REVIEWS_PER_APP))
        df.insert(0, "app", name)
        out = RAW_DIR / f"{app_id}.parquet"
        df.to_parquet(out, index=False)
        print(f"  saved {len(df)} rows -> {out.name}")


if __name__ == "__main__":
    main()
