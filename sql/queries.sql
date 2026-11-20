-- Analysis queries for the UPI app review dataset (SQLite).
-- Each query starts with "-- name: <id>" so src/sqlq.py can load it by name.
-- Tables: reviews(review_id, app, rating, content, ..., month, version_major, has_reply, reply_hours)
--         review_themes(review_id, theme)

-- name: app_summary
-- Headline KPIs per app. Restricted to the date window every app covers
-- (in_common_window = 1) so the apps are compared like for like.
SELECT
    app,
    COUNT(*)                                        AS reviews,
    ROUND(AVG(rating), 2)                           AS avg_rating,
    ROUND(100.0 * SUM(rating = 1) / COUNT(*), 1)    AS pct_one_star,
    ROUND(100.0 * SUM(rating = 5) / COUNT(*), 1)    AS pct_five_star,
    ROUND(100.0 * SUM(has_reply) / COUNT(*), 1)     AS pct_replied,
    MIN(review_date)                                AS first_review,
    MAX(review_date)                                AS last_review
FROM reviews
WHERE in_common_window = 1
GROUP BY app
ORDER BY avg_rating DESC;

-- name: app_kpis
-- Same KPIs without the common-window restriction (the dashboard applies its own date filter).
SELECT app, COUNT(*) AS reviews, ROUND(AVG(rating), 2) AS avg_rating,
       ROUND(100.0 * SUM(rating = 1) / COUNT(*), 1) AS pct_one_star
FROM reviews
GROUP BY app
ORDER BY avg_rating DESC;

-- name: rating_distribution
-- Star distribution per app (common window).
SELECT app, rating, COUNT(*) AS reviews,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY app), 1) AS pct
FROM reviews
WHERE in_common_window = 1
GROUP BY app, rating
ORDER BY app, rating;

-- name: daily_trend
-- Daily average rating with a 7-day rolling average (window function).
-- Days with fewer than 50 reviews are dropped as too noisy.
WITH daily AS (
    SELECT app, review_date, COUNT(*) AS reviews, AVG(rating) AS avg_rating,
           100.0 * SUM(rating = 1) / COUNT(*) AS pct_one_star
    FROM reviews
    GROUP BY app, review_date
    HAVING COUNT(*) >= 50
)
SELECT app, review_date, reviews,
       ROUND(avg_rating, 2)   AS avg_rating,
       ROUND(pct_one_star, 1) AS pct_one_star,
       ROUND(AVG(avg_rating) OVER (
           PARTITION BY app ORDER BY review_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_7d
FROM daily
ORDER BY app, review_date;

-- name: version_ratings
-- Rating per app version, ordered by release (first review date), with the change
-- versus the previous version (LAG). Versions with < 150 reviews are excluded.
WITH v AS (
    SELECT app, version_major, COUNT(*) AS reviews, AVG(rating) AS avg_rating,
           MIN(review_date) AS first_seen
    FROM reviews
    WHERE version_major IS NOT NULL
    GROUP BY app, version_major
    HAVING COUNT(*) >= 150
)
SELECT app, version_major, first_seen, reviews,
       ROUND(avg_rating, 2) AS avg_rating,
       ROUND(avg_rating - LAG(avg_rating) OVER (PARTITION BY app ORDER BY first_seen), 2) AS change_vs_prev
FROM v
ORDER BY app, first_seen;

-- name: worst_version
-- The lowest-rated version of each app (CTE + ROW_NUMBER).
WITH v AS (
    SELECT app, version_major, COUNT(*) AS reviews, ROUND(AVG(rating), 2) AS avg_rating
    FROM reviews
    WHERE version_major IS NOT NULL
    GROUP BY app, version_major
    HAVING COUNT(*) >= 150
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY app ORDER BY avg_rating) AS rn FROM v
)
SELECT app, version_major, reviews, avg_rating FROM ranked WHERE rn = 1;

-- name: complaint_themes
-- Share of an app's negative (1-2 star) English reviews of 3+ words that mention each theme.
-- A review can mention several themes, so shares do not sum to 100.
WITH neg AS (
    SELECT review_id, app FROM reviews WHERE rating <= 2 AND is_english = 1 AND word_count >= 3
), totals AS (
    SELECT app, COUNT(*) AS n FROM neg GROUP BY app
)
SELECT neg.app, t.theme, COUNT(*) AS reviews,
       ROUND(100.0 * COUNT(*) / totals.n, 1) AS pct_of_negative
FROM neg
JOIN review_themes t ON t.review_id = neg.review_id
JOIN totals ON totals.app = neg.app
WHERE t.theme <> 'Praise'
GROUP BY neg.app, t.theme
ORDER BY neg.app, pct_of_negative DESC;

-- name: theme_rating
-- Average rating of reviews that mention each theme vs. the overall average:
-- which issues hurt the score the most.
SELECT t.theme,
       COUNT(*)                                       AS reviews,
       ROUND(AVG(r.rating), 2)                        AS avg_rating,
       ROUND(AVG(r.rating) - (SELECT AVG(rating) FROM reviews WHERE is_english = 1 AND word_count >= 3), 2) AS vs_overall
FROM review_themes t
JOIN reviews r ON r.review_id = t.review_id
GROUP BY t.theme
ORDER BY avg_rating;

-- name: daily_themes
-- Daily count of negative reviews per complaint theme (for spotting incidents).
SELECT r.app, r.review_date, t.theme, COUNT(*) AS reviews
FROM reviews r
JOIN review_themes t ON t.review_id = r.review_id
WHERE r.rating <= 2 AND t.theme <> 'Praise'
GROUP BY r.app, r.review_date, t.theme
ORDER BY r.app, r.review_date;

-- name: reply_stats
-- Developer response: reply rate on negative reviews and median reply time.
-- SQLite has no MEDIAN(), so it is computed with ROW_NUMBER over the sorted values.
WITH neg AS (
    SELECT app, has_reply, reply_hours FROM reviews WHERE rating <= 2
), ordered AS (
    SELECT app, reply_hours,
           ROW_NUMBER() OVER (PARTITION BY app ORDER BY reply_hours) AS rn,
           COUNT(*)     OVER (PARTITION BY app)                      AS n
    FROM neg
    WHERE has_reply = 1 AND reply_hours >= 0
), medians AS (
    SELECT app, AVG(reply_hours) AS median_hours
    FROM ordered
    WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
    GROUP BY app
)
SELECT neg.app,
       COUNT(*)                                        AS negative_reviews,
       ROUND(100.0 * SUM(neg.has_reply) / COUNT(*), 1) AS pct_replied,
       ROUND(medians.median_hours, 1)                  AS median_reply_hours
FROM neg
LEFT JOIN medians ON medians.app = neg.app
GROUP BY neg.app
ORDER BY pct_replied DESC;

-- name: top_liked_complaints
-- The negative reviews other users agreed with most (thumbs up).
SELECT app, rating, thumbs_up, review_date, content
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY app ORDER BY thumbs_up DESC) AS rn
    FROM reviews
    WHERE rating <= 2 AND is_english = 1
)
WHERE rn <= 5
ORDER BY app, thumbs_up DESC;

-- name: coverage
-- How much data each app contributes, and over what dates.
SELECT app, COUNT(*) AS reviews, MIN(review_date) AS first_day, MAX(review_date) AS last_day,
       ROUND(COUNT(*) * 1.0 / (julianday(MAX(review_date)) - julianday(MIN(review_date)) + 1)) AS reviews_per_day,
       ROUND(100.0 * SUM(word_count < 3) / COUNT(*), 1) AS pct_under_3_words
FROM reviews
GROUP BY app;

-- name: length_vs_rating
-- Do unhappy users write longer reviews?
SELECT rating, COUNT(*) AS reviews, ROUND(AVG(word_count), 1) AS avg_words
FROM reviews
GROUP BY rating
ORDER BY rating;
