-- Phase 6 read-only representative reporting-query performance checks.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
USE `MSM_dataset_UAT`;
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;

EXPLAIN ANALYZE
SELECT DATE_FORMAT(`published_date`, '%Y-%m') AS `month`, `tone_sentiment`,
       COUNT(*) AS `article_count`
FROM `UAT_articles`
WHERE `published_date` >= '2026-01-01' AND `published_date` < '2026-08-01'
GROUP BY DATE_FORMAT(`published_date`, '%Y-%m'), `tone_sentiment`
ORDER BY `month`, `tone_sentiment`;

EXPLAIN ANALYZE
SELECT `topic`, COUNT(*) AS `topic_count`
FROM `UAT_articles`
WHERE `published_date` >= '2026-01-22'
  AND `published_date` < '2026-07-23'
  AND `topic` IS NOT NULL AND `topic` <> ''
GROUP BY `topic`
ORDER BY `topic_count` DESC, `topic` ASC
LIMIT 10;

EXPLAIN ANALYZE
SELECT *
FROM `UAT_v_article_coverage_summary`
WHERE `article_id` = 1164520;

EXPLAIN ANALYZE
SELECT `publish_date`, `coverage_type`, SUM(`article_count`) AS `article_count`
FROM `UAT_v_outlet_daily_volume`
WHERE `publish_date` >= '2026-01-01' AND `publish_date` < '2026-08-01'
GROUP BY `publish_date`, `coverage_type`
ORDER BY `publish_date`, `coverage_type`;

COMMIT;
