"""Load named queries from sql/queries.sql and run them against the SQLite db."""
import re
import sqlite3
from functools import lru_cache

import pandas as pd

from config import DB_PATH, ROOT


@lru_cache
def queries() -> dict[str, str]:
    text = (ROOT / "sql" / "queries.sql").read_text()
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run(name: str, db=DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db) as con:
        return pd.read_sql(queries()[name], con)


def run_filtered(names: list[str], apps: list[str], start: str, end: str,
                 ratings: list[int], db=DB_PATH) -> dict[str, pd.DataFrame]:
    """Run the same named queries on a filtered slice of the data.

    A TEMP view called `reviews` shadows the real table (SQLite resolves temp objects
    first), so every query in queries.sql works unchanged on the filtered rows.
    Values are interpolated only after validation against fixed types/lists.
    """
    known = {"PhonePe", "Google Pay", "Paytm"}
    apps = [a for a in apps if a in known] or ["__none__"]
    ratings = [int(r) for r in ratings if int(r) in range(1, 6)] or [0]
    start, end = str(pd.Timestamp(start).date()), str(pd.Timestamp(end).date())
    app_list = ",".join(f"'{a}'" for a in apps)
    rating_list = ",".join(map(str, ratings))
    with sqlite3.connect(db) as con:
        con.execute(
            f"CREATE TEMP VIEW reviews AS SELECT * FROM main.reviews "
            f"WHERE app IN ({app_list}) AND rating IN ({rating_list}) "
            f"AND review_date BETWEEN '{start}' AND '{end}'"
        )
        return {n: pd.read_sql(queries()[n], con) for n in names}
