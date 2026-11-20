"""Streamlit dashboard: what users complain about in India's top UPI apps."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import COMPLAINT_THEMES, DB_PATH  # noqa: E402
from sqlq import run_filtered  # noqa: E402

APP_COLORS = {"PhonePe": "#5f259f", "Google Pay": "#1a73e8", "Paytm": "#00b9f1"}

st.set_page_config(page_title="UPI App Reviews", layout="wide")


@st.cache_data
def bounds():
    with sqlite3.connect(DB_PATH) as con:
        lo, hi, common = con.execute(
            "SELECT MIN(review_date), MAX(review_date), MIN(CASE WHEN in_common_window = 1 THEN review_date END) FROM reviews"
        ).fetchone()
    return pd.Timestamp(lo).date(), pd.Timestamp(hi).date(), pd.Timestamp(common).date()


@st.cache_data
def data(apps, start, end, ratings):
    out = run_filtered(
        ["app_kpis", "daily_trend", "complaint_themes", "version_ratings", "reply_stats", "theme_rating"],
        list(apps), start, end, list(ratings),
    )
    return out


@st.cache_data
def sample_reviews(app, theme, n=25):
    q = """SELECT r.rating, r.review_date, r.thumbs_up, r.content
           FROM reviews r JOIN review_themes t ON t.review_id = r.review_id
           WHERE r.app = ? AND t.theme = ? AND r.rating <= 2
           ORDER BY r.thumbs_up DESC, r.review_date DESC LIMIT ?"""
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql(q, con, params=(app, theme, n))


st.title("What users complain about in India's top UPI apps")
st.caption("Google Play reviews (India store) of PhonePe, Google Pay and Paytm, sorted into complaint themes. "
           "Google Pay gets ~4,300 reviews a day, so its 30k reviews cover only ~6 days; the headline tiles use "
           "only the dates all three apps cover.")

lo, hi, common = bounds()
with st.sidebar:
    st.header("Filters")
    apps = st.multiselect("Apps", list(APP_COLORS), default=list(APP_COLORS))
    dr = st.date_input("Date range", (common, hi), min_value=lo, max_value=hi,
                       help="Defaults to the dates all three apps cover. Widen it to see PhonePe and Paytm "
                            "back to September (Google Pay data starts mid-November).")
    ratings = st.multiselect("Star rating", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])
start, end = (dr if isinstance(dr, tuple) and len(dr) == 2 else (common, hi))

if not apps or not ratings:
    st.warning("Select at least one app and one rating.")
    st.stop()

d = data(tuple(apps), str(start), str(end), tuple(ratings))
summary = d["app_kpis"]
if summary.empty:
    st.warning("No reviews match these filters.")
    st.stop()

cols = st.columns(len(summary))
for col, row in zip(cols, summary.itertuples()):
    with col:
        st.subheader(row.app)
        a, b, c = st.columns(3)
        a.metric("Avg rating", f"{row.avg_rating:.2f}★")
        b.metric("1-star share", f"{row.pct_one_star:.0f}%")
        c.metric("Reviews", f"{row.reviews:,}")

st.divider()
left, right = st.columns(2)
with left:
    st.subheader("Rating trend (7-day rolling)")
    mt = d["daily_trend"]
    if mt.empty:
        st.info("Not enough reviews per day for a trend in this slice.")
    else:
        fig = px.line(mt, x="review_date", y="rolling_7d", color="app",
                      color_discrete_map=APP_COLORS, labels={"rolling_7d": "Avg rating", "review_date": ""})
        st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("What 1–2★ reviews complain about")
    ct = d["complaint_themes"]
    if ct.empty:
        st.info("Include 1 or 2 star ratings to see complaint themes.")
    else:
        fig = px.bar(ct, y="theme", x="pct_of_negative", color="app", barmode="group", orientation="h",
                     color_discrete_map=APP_COLORS,
                     labels={"pct_of_negative": "% of negative reviews", "theme": ""},
                     category_orders={"theme": COMPLAINT_THEMES})
        st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Rating by app version")
    vr = d["version_ratings"]
    if vr.empty:
        st.info("Not enough reviews per version in this slice.")
    else:
        fig = px.line(vr, x="version_major", y="avg_rating", color="app", markers=True, facet_col="app",
                      hover_data=["reviews", "change_vs_prev"], color_discrete_map=APP_COLORS,
                      labels={"version_major": "Version (release order)", "avg_rating": "Avg rating"})
        fig.update_xaxes(matches=None, type="category")
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Which issues hurt the rating most")
    tr = d["theme_rating"]
    tr = tr[tr["theme"] != "Praise"]
    fig = px.bar(tr, x="vs_overall", y="theme", orientation="h",
                 labels={"vs_overall": "Avg rating vs. overall", "theme": ""})
    st.plotly_chart(fig, width="stretch")

st.subheader("Developer replies to negative reviews")
st.dataframe(d["reply_stats"].rename(columns={
    "app": "App", "negative_reviews": "1–2★ reviews", "pct_replied": "% replied",
    "median_reply_hours": "Median reply time (h)"}), hide_index=True, width="stretch")

st.divider()
st.subheader("Read the reviews")
c1, c2 = st.columns(2)
app_pick = c1.selectbox("App", apps)
theme_pick = c2.selectbox("Theme", COMPLAINT_THEMES)
st.dataframe(sample_reviews(app_pick, theme_pick), hide_index=True, width="stretch")
st.caption("Most-liked 1–2★ reviews for the theme across the full period. Usernames are never stored.")
