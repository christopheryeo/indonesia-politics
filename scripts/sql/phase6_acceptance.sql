-- Phase 6 comprehensive post-load UAT acceptance audit.
-- SELECT/CHECKSUM only. Production is never referenced.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
USE `MSM_dataset_UAT`;

SET @load_id = 'a44faa80-c422-4078-a302-f3676fe2434b';
SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;

SELECT 'phase5_gate' AS `check_name`, `status`, `loaded_article_count`,
       `loaded_coverage_count`, `loaded_media_count`, `loaded_tag_count`,
       `loaded_user_group_count`
FROM `UAT_p5_load_batches`
WHERE `load_id` = @load_id;

SELECT 'canonical_counts' AS `check_name`,
  (SELECT COUNT(*) FROM `UAT_articles`) AS `articles`,
  (SELECT COUNT(*) FROM `UAT_article_coverage`) AS `coverage`,
  (SELECT COUNT(*) FROM `UAT_article_media`) AS `media`,
  (SELECT COUNT(*) FROM `UAT_article_tags`) AS `tags`,
  (SELECT COUNT(*) FROM `UAT_article_user_groups`) AS `user_groups`;

SELECT 'relational_failures' AS `check_name`,
  (SELECT COUNT(*) FROM `UAT_article_coverage` c LEFT JOIN `UAT_articles` a ON a.`article_id` = c.`article_id` WHERE a.`article_id` IS NULL) AS `coverage_orphans`,
  (SELECT COUNT(*) FROM `UAT_article_media` m LEFT JOIN `UAT_articles` a ON a.`article_id` = m.`article_id` WHERE a.`article_id` IS NULL) AS `media_orphans`,
  (SELECT COUNT(*) FROM `UAT_article_tags` t LEFT JOIN `UAT_articles` a ON a.`article_id` = t.`article_id` WHERE a.`article_id` IS NULL) AS `tag_orphans`,
  (SELECT COUNT(*) FROM `UAT_article_user_groups` u LEFT JOIN `UAT_articles` a ON a.`article_id` = u.`article_id` WHERE a.`article_id` IS NULL) AS `user_group_orphans`,
  (SELECT COUNT(*) - COUNT(DISTINCT `article_id`) FROM `UAT_articles`) AS `duplicate_article_primary_keys`,
  (SELECT COUNT(*) - COUNT(DISTINCT `id`) FROM `UAT_article_coverage`) AS `duplicate_coverage_primary_keys`,
  (SELECT COUNT(*) - COUNT(DISTINCT `id`) FROM `UAT_article_media`) AS `duplicate_media_primary_keys`,
  (SELECT COUNT(*) - COUNT(DISTINCT `id`) FROM `UAT_article_tags`) AS `duplicate_tag_primary_keys`,
  (SELECT COUNT(*) - COUNT(DISTINCT `id`) FROM `UAT_article_user_groups`) AS `duplicate_user_group_primary_keys`;

SELECT 'loaded_business_rule_failures' AS `check_name`,
  SUM(a.`document_id` IS NULL) AS `null_document_id`,
  SUM(a.`category` IS NULL OR a.`category` = '') AS `missing_category`,
  SUM(a.`tone` IS NULL OR a.`tone` NOT IN ('Factual','Opinionated')) AS `invalid_tone`,
  SUM(a.`tone_sentiment` IS NULL OR a.`tone_sentiment` NOT IN ('Positive','Neutral')) AS `invalid_sentiment`,
  SUM(a.`event_type` IS NULL OR a.`event_type` NOT IN ('Facilitated','Unfacilitated')) AS `invalid_event_type`,
  SUM(a.`article_status` IS NULL OR a.`article_status` <> 'A') AS `invalid_article_status`,
  SUM(a.`product_type` IS NULL OR a.`product_type` <> 'FEED') AS `invalid_product_type`,
  SUM(a.`published_date` IS NULL) AS `null_published_date`
FROM `UAT_articles` a
JOIN `UAT_p4_articles` p
  ON p.`article_id` = a.`article_id` AND p.`transform_id` = @transform_id;

SELECT 'loaded_child_cardinality_failures' AS `check_name`,
  SUM(x.`coverage_count` <> 1) AS `not_one_coverage`,
  SUM(x.`tag_count` < 1) AS `zero_tags`,
  SUM(x.`user_group_count` <> 1) AS `not_one_user_group`
FROM (
  SELECT p.`article_id`,
    (SELECT COUNT(*) FROM `UAT_article_coverage` c WHERE c.`article_id` = p.`article_id`) AS `coverage_count`,
    (SELECT COUNT(*) FROM `UAT_article_tags` t WHERE t.`article_id` = p.`article_id`) AS `tag_count`,
    (SELECT COUNT(*) FROM `UAT_article_user_groups` u WHERE u.`article_id` = p.`article_id`) AS `user_group_count`
  FROM `UAT_p4_articles` p
  WHERE p.`transform_id` = @transform_id
) x;

SELECT 'held_loaded' AS `check_name`, COUNT(*) AS `failure_count`
FROM `UAT_p4_holds` h
JOIN `UAT_articles` a ON a.`article_id` = h.`target_article_id`
WHERE h.`transform_id` = @transform_id;

SELECT 'loaded_vendor_duplicates_with_preexisting' AS `check_name`,
       COUNT(*) AS `matching_pairs`, COUNT(DISTINCT p.`article_id`) AS `loaded_articles`
FROM `UAT_p4_articles` p
JOIN `UAT_articles` a
  ON a.`vendor_article_id` = p.`vendor_article_id`
 AND a.`article_id` <> p.`article_id`
LEFT JOIN `UAT_p4_articles` other_loaded
  ON other_loaded.`transform_id` = p.`transform_id`
 AND other_loaded.`article_id` = a.`article_id`
WHERE p.`transform_id` = @transform_id
  AND p.`vendor_article_id` IS NOT NULL
  AND other_loaded.`article_id` IS NULL;

SELECT 'loaded_exact_duplicates_with_preexisting' AS `check_name`,
       COUNT(*) AS `matching_pairs`, COUNT(DISTINCT p.`article_id`) AS `loaded_articles`
FROM `UAT_p4_articles` p
JOIN `UAT_articles` a
  ON a.`vendor_article_id` = p.`vendor_article_id`
 AND a.`article_title` <=> p.`article_title`
 AND a.`published_date` <=> p.`published_date`
 AND a.`article_id` <> p.`article_id`
LEFT JOIN `UAT_p4_articles` other_loaded
  ON other_loaded.`transform_id` = p.`transform_id`
 AND other_loaded.`article_id` = a.`article_id`
WHERE p.`transform_id` = @transform_id
  AND p.`vendor_article_id` IS NOT NULL
  AND other_loaded.`article_id` IS NULL;

WITH base AS (
  SELECT a.`article_id`, a.`article_title`, a.`category`, a.`tone`, a.`tone_sentiment`,
         a.`event_type`, a.`published_date`,
         SUM(c.`coverage_type` = 'broadcast') AS `broadcast_count`,
         SUM(c.`coverage_type` = 'online') AS `online_count`,
         SUM(c.`coverage_type` = 'print') AS `print_count`,
         COUNT(c.`id`) AS `total_coverage_count`,
         COUNT(DISTINCT c.`display_name`) AS `unique_outlets`
  FROM `UAT_articles` a
  LEFT JOIN `UAT_article_coverage` c ON c.`article_id` = a.`article_id`
  GROUP BY a.`article_id`, a.`article_title`, a.`category`, a.`tone`,
           a.`tone_sentiment`, a.`event_type`, a.`published_date`
)
SELECT 'coverage_summary_view_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM base b
LEFT JOIN `UAT_v_article_coverage_summary` v ON v.`article_id` = b.`article_id`
WHERE v.`article_id` IS NULL
   OR NOT (
     v.`article_title` <=> b.`article_title`
     AND v.`category` <=> b.`category`
     AND v.`tone` <=> b.`tone`
     AND v.`tone_sentiment` <=> b.`tone_sentiment`
     AND v.`event_type` <=> b.`event_type`
     AND v.`published_date` <=> b.`published_date`
     AND v.`broadcast_count` <=> b.`broadcast_count`
     AND v.`online_count` <=> b.`online_count`
     AND v.`print_count` <=> b.`print_count`
     AND v.`total_coverage_count` <=> b.`total_coverage_count`
     AND v.`unique_outlets` <=> b.`unique_outlets`
   );

WITH base AS (
  SELECT CAST(a.`published_date` AS date) AS `publish_date`, c.`coverage_type`,
         c.`display_name` AS `outlet`, c.`country`, a.`category`, a.`tone_sentiment`,
         COUNT(DISTINCT a.`article_id`) AS `article_count`
  FROM `UAT_articles` a
  JOIN `UAT_article_coverage` c ON c.`article_id` = a.`article_id`
  GROUP BY CAST(a.`published_date` AS date), c.`coverage_type`, c.`display_name`,
           c.`country`, a.`category`, a.`tone_sentiment`
), differences AS (
  SELECT b.`publish_date`
  FROM base b
  LEFT JOIN `UAT_v_outlet_daily_volume` v
    ON v.`publish_date` <=> b.`publish_date`
   AND v.`coverage_type` <=> b.`coverage_type`
   AND v.`outlet` <=> b.`outlet`
   AND v.`country` <=> b.`country`
   AND v.`category` <=> b.`category`
   AND v.`tone_sentiment` <=> b.`tone_sentiment`
   AND v.`article_count` <=> b.`article_count`
  WHERE v.`article_count` IS NULL
  UNION ALL
  SELECT v.`publish_date`
  FROM `UAT_v_outlet_daily_volume` v
  LEFT JOIN base b
    ON b.`publish_date` <=> v.`publish_date`
   AND b.`coverage_type` <=> v.`coverage_type`
   AND b.`outlet` <=> v.`outlet`
   AND b.`country` <=> v.`country`
   AND b.`category` <=> v.`category`
   AND b.`tone_sentiment` <=> v.`tone_sentiment`
   AND b.`article_count` <=> v.`article_count`
  WHERE b.`article_count` IS NULL
)
SELECT 'outlet_daily_view_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM differences;

SELECT 'coverage_type_reconciliation' AS `check_name`, x.`coverage_type`,
       x.`base_count`, x.`view_count`, x.`base_count` - x.`view_count` AS `difference`
FROM (
  SELECT 'broadcast' AS `coverage_type`,
    (SELECT COUNT(*) FROM `UAT_article_coverage` WHERE `coverage_type` = 'broadcast') AS `base_count`,
    (SELECT SUM(`broadcast_count`) FROM `UAT_v_article_coverage_summary`) AS `view_count`
  UNION ALL
  SELECT 'online',
    (SELECT COUNT(*) FROM `UAT_article_coverage` WHERE `coverage_type` = 'online'),
    (SELECT SUM(`online_count`) FROM `UAT_v_article_coverage_summary`)
  UNION ALL
  SELECT 'print',
    (SELECT COUNT(*) FROM `UAT_article_coverage` WHERE `coverage_type` = 'print'),
    (SELECT SUM(`print_count`) FROM `UAT_v_article_coverage_summary`)
) x;

WITH base AS (
  SELECT DATE_FORMAT(`published_date`, '%Y-%m') AS `month`, `tone_sentiment` AS `sentiment`,
         COUNT(*) AS `article_count`
  FROM `UAT_articles`
  GROUP BY DATE_FORMAT(`published_date`, '%Y-%m'), `tone_sentiment`
), via_view AS (
  SELECT DATE_FORMAT(`published_date`, '%Y-%m') AS `month`, `tone_sentiment` AS `sentiment`,
         COUNT(*) AS `article_count`
  FROM `UAT_v_article_coverage_summary`
  GROUP BY DATE_FORMAT(`published_date`, '%Y-%m'), `tone_sentiment`
)
SELECT 'monthly_sentiment_reporting_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM base b
LEFT JOIN via_view v
  ON v.`month` <=> b.`month` AND v.`sentiment` <=> b.`sentiment`
WHERE v.`month` IS NULL OR v.`article_count` <> b.`article_count`;

SELECT 'monthly_sentiment' AS `report_name`,
       DATE_FORMAT(`published_date`, '%Y-%m') AS `month`,
       `tone_sentiment` AS `sentiment`, COUNT(*) AS `article_count`
FROM `UAT_articles`
WHERE `published_date` >= '2026-01-01' AND `published_date` < '2026-08-01'
GROUP BY DATE_FORMAT(`published_date`, '%Y-%m'), `tone_sentiment`
ORDER BY `month`, `sentiment`;

SELECT 'top_topics_six_months' AS `report_name`, `topic`, COUNT(*) AS `topic_count`
FROM `UAT_articles`
WHERE `published_date` >= '2026-01-22'
  AND `published_date` < '2026-07-23'
  AND `topic` IS NOT NULL AND `topic` <> ''
GROUP BY `topic`
ORDER BY `topic_count` DESC, `topic` ASC
LIMIT 10;

SELECT 'whole_table_value' AS `check_name`, 'tone' AS `field_name`, `tone` AS `field_value`, COUNT(*) AS `row_count`
FROM `UAT_articles` GROUP BY `tone`
UNION ALL
SELECT 'whole_table_value', 'tone_sentiment', `tone_sentiment`, COUNT(*)
FROM `UAT_articles` GROUP BY `tone_sentiment`
UNION ALL
SELECT 'whole_table_value', 'event_type', `event_type`, COUNT(*)
FROM `UAT_articles` GROUP BY `event_type`
UNION ALL
SELECT 'whole_table_value', 'coverage_type', `coverage_type`, COUNT(*)
FROM `UAT_article_coverage` GROUP BY `coverage_type`
ORDER BY `field_name`, `field_value`;

COMMIT;

CHECKSUM TABLE
  `UAT_articles`, `UAT_article_coverage`, `UAT_article_media`,
  `UAT_article_tags`, `UAT_article_user_groups`,
  `UAT_v_article_coverage_summary`, `UAT_v_outlet_daily_volume`;
