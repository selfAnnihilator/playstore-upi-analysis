"""Generate notebooks/analysis.ipynb (kept as a script so the notebook is reproducible and diff-friendly)."""
from pathlib import Path

import nbformat as nbf

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("# What users complain about in India's top UPI apps\n"
       "Google Play reviews of **PhonePe, Google Pay and Paytm** (English, India store), scraped with "
       "`google-play-scraper`, cleaned into SQLite and analysed with SQL (`sql/queries.sql`).\n\n"
       "**Questions**\n"
       "1. How do the three apps compare on rating, and how has that changed over time?\n"
       "2. What do unhappy users complain about, and does it differ by app?\n"
       "3. Which app versions coincided with a drop in rating?\n"
       "4. Which issues hurt the rating most?\n"
       "5. How well do the developers respond to negative reviews?"),
    code("import sys, sqlite3\nfrom pathlib import Path\n"
         "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n"
         "import pandas as pd\nimport plotly.express as px\nimport plotly.io as pio\n"
         "from config import DB_PATH, FIG_DIR, COMPLAINT_THEMES\nfrom sqlq import run\n"
         "pio.renderers.default = 'png'\nFIG_DIR.mkdir(parents=True, exist_ok=True)\n"
         "COLORS = {'PhonePe': '#5f259f', 'Google Pay': '#1a73e8', 'Paytm': '#00b9f1'}\n"
         "pd.set_option('display.max_colwidth', 160)\n"
         "def save(fig, name):\n"
         "    fig.update_layout(template='plotly_white', width=1000, height=520)\n"
         "    fig.write_image(FIG_DIR / f'{name}.png', scale=2)\n"
         "    return fig"),
    md("## 1. Data overview and quality checks"),
    code("with sqlite3.connect(DB_PATH) as con:\n"
         "    checks = pd.read_sql('''SELECT COUNT(*) AS rows, COUNT(DISTINCT review_id) AS unique_ids,\n"
         "        SUM(rating IS NULL) AS null_ratings, SUM(content IS NULL OR content = '') AS empty_text,\n"
         "        ROUND(AVG(is_english), 3) AS share_english, MIN(review_date) AS first, MAX(review_date) AS last\n"
         "        FROM reviews''', con)\n"
         "checks"),
    code("run('coverage')"),
    md("**Coverage differs by app.** Each app has 30k reviews, but Google Pay gets far more reviews per day, so its 30k "
       "span only about a week. Rating comparisons between apps therefore use only the dates all three cover "
       "(`in_common_window = 1`). Theme shares use each app's full sample."),
    code("summary = run('app_summary'); summary"),
    code("dist = run('rating_distribution')\n"
         "save(px.bar(dist, x='rating', y='pct', color='app', barmode='group', color_discrete_map=COLORS,\n"
         "            title='Rating distribution (% of each app\\'s reviews)', labels={'pct': '%', 'rating': 'Stars'}),\n"
         "     'rating_distribution')"),
    md("Play Store reviews are **J-shaped**: mostly 5★ and 1★. Reviews are written by users who feel strongly, so they "
       "measure *what goes wrong*, not overall satisfaction."),
    md("## 2. Rating over time"),
    code("trend = run('daily_trend')\n"
         "save(px.line(trend, x='review_date', y='rolling_7d', color='app', color_discrete_map=COLORS,\n"
         "             title='Average rating, 7-day rolling', labels={'rolling_7d': 'Avg rating', 'review_date': ''}),\n"
         "     'daily_trend')"),
    code("trend.sort_values('pct_one_star', ascending=False).head(8)"),
    md("## 3. What do 1–2★ reviews complain about?"),
    code("themes = run('complaint_themes')\n"
         "save(px.bar(themes, y='theme', x='pct_of_negative', color='app', barmode='group', orientation='h',\n"
         "            color_discrete_map=COLORS, category_orders={'theme': COMPLAINT_THEMES},\n"
         "            title='Share of negative reviews mentioning each theme', labels={'pct_of_negative': '% of 1–2★ reviews', 'theme': ''}),\n"
         "     'complaint_themes')"),
    code("themes.pivot(index='theme', columns='app', values='pct_of_negative').sort_values('PhonePe', ascending=False)"),
    md("## 4. Which issues hurt the rating most?"),
    code("tr = run('theme_rating').query(\"theme != 'Praise'\")\n"
         "save(px.bar(tr, x='vs_overall', y='theme', orientation='h', title='Average rating of reviews mentioning a theme, vs. overall',\n"
         "            labels={'vs_overall': 'Stars vs. overall average', 'theme': ''}), 'theme_rating')"),
    md("## 5. App versions"),
    code("vr = run('version_ratings')\n"
         "fig = px.line(vr, x='version_major', y='avg_rating', color='app', markers=True, facet_col='app',\n"
         "              color_discrete_map=COLORS, title='Average rating by app version (release order)',\n"
         "              labels={'version_major': 'Version', 'avg_rating': 'Avg rating'})\n"
         "fig.update_xaxes(matches=None, type='category')\n"
         "fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1]))\n"
         "save(fig.update_layout(showlegend=False), 'version_ratings')"),
    code("vr.sort_values('change_vs_prev').head(8)"),
    code("run('worst_version')"),
    md("## 6. Developer responses"),
    code("run('reply_stats')"),
    md("## 7. Supporting checks"),
    code("run('length_vs_rating')"),
    code("run('top_liked_complaints')"),
    md("### Theme discovery check (TF-IDF + NMF)\n"
       "To check the keyword taxonomy isn't missing a major issue, cluster untagged negative reviews and look at the top words."),
    code("from sklearn.feature_extraction.text import TfidfVectorizer\nfrom sklearn.decomposition import NMF\n"
         "with sqlite3.connect(DB_PATH) as con:\n"
         "    untagged = pd.read_sql('''SELECT content FROM reviews r WHERE rating <= 2 AND is_english = 1 AND word_count >= 3\n"
         "        AND NOT EXISTS (SELECT 1 FROM review_themes t WHERE t.review_id = r.review_id AND t.theme <> 'Praise')''', con)\n"
         "print(f'{len(untagged):,} untagged negative reviews')\n"
         "vec = TfidfVectorizer(stop_words='english', min_df=10, max_df=0.5, ngram_range=(1, 2))\n"
         "X = vec.fit_transform(untagged['content'])\n"
         "nmf = NMF(n_components=8, random_state=0).fit(X)\n"
         "words = vec.get_feature_names_out()\n"
         "for i, comp in enumerate(nmf.components_):\n"
         "    print(i, ', '.join(words[comp.argsort()[-10:][::-1]]))"),
    md(Path(__file__).with_name("insights.md").read_text()),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.write(nb, Path(__file__).with_name("analysis.ipynb"))
print("wrote analysis.ipynb")
