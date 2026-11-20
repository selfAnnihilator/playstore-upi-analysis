"""Tag each review with complaint themes using the keyword taxonomy in config.THEMES.

Writes table `review_themes(review_id, theme)` (one row per review-theme pair) and
prints coverage stats plus a random sample for manual spot-checking.
"""
import re
import sqlite3
import sys

import pandas as pd

from clean import MIN_WORDS
from config import COMPLAINT_THEMES, DB_PATH, THEMES

PATTERNS = {t: re.compile(r"\b(?:" + "|".join(ps) + r")\b", re.I) for t, ps in THEMES.items()}


def tag(text: str, rating: int) -> list[str]:
    found = [t for t, p in PATTERNS.items() if p.search(text)]
    # "Praise" only counts on happy reviews; "good app but payment failed" at 2★ is a complaint.
    if rating <= 3:
        found = [t for t in found if t != "Praise"]
    return found


def main() -> None:
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql("SELECT review_id, app, rating, content FROM reviews WHERE is_english = 1 AND word_count >= ?",
                         con, params=(MIN_WORDS,))
        df["themes"] = [tag(c, r) for c, r in zip(df["content"], df["rating"])]
        pairs = df[["review_id", "themes"]].explode("themes").dropna()
        pairs.rename(columns={"themes": "theme"}).to_sql("review_themes", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_rt_review ON review_themes(review_id)")

    neg = df[df["rating"] <= 2]
    covered = neg["themes"].map(lambda ts: any(t in COMPLAINT_THEMES for t in ts)).mean()
    print(f"tagged {len(df)} English reviews with >= {MIN_WORDS} words; {covered:.1%} of 1-2 star reviews got a complaint theme")

    if "--sample" in sys.argv:
        for _, r in neg.sample(50, random_state=1).iterrows():
            print(f"\n[{r.app} {r.rating}*] {', '.join(r.themes) or '-'}\n  {r.content[:220]}")


if __name__ == "__main__":
    main()
