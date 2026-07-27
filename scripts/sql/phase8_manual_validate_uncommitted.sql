-- Phase 8 in-transaction validation for the manual production load.
-- Run in the SAME session as phase8_manual_load_uncommitted.sql.
-- Every failure_count must be zero. This script does not COMMIT.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';

SELECT 'insert_count_mismatch' AS `check_name`,
       (@phase8_inserted_articles <> 8140)
     + (@phase8_inserted_coverage <> 8140)
     + (@phase8_inserted_media <> 343)
     + (@phase8_inserted_tags <> 227222)
     + (@phase8_inserted_user_groups <> 8140) AS `failure_count`;

SELECT 'target_total_mismatch' AS `check_name`,
       ((SELECT COUNT(*) FROM `MSM_dataset`.`articles`) <> @phase8_before_articles + 8140)
     + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage`) <> @phase8_before_coverage + 8140)
     + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_media`) <> @phase8_before_media + 343)
     + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_tags`) <> @phase8_before_tags + 227222)
     + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups`) <> @phase8_before_user_groups + 8140)
       AS `failure_count`;

SELECT 'article_missing_or_field_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id` = p.`article_id`
WHERE p.`transform_id` = @transform_id
  AND (a.`article_id` IS NULL OR NOT (
    a.`document_id` <=> p.`document_id`
    AND a.`vendor_article_id` <=> p.`vendor_article_id`
    AND a.`article_title` <=> p.`article_title`
    AND a.`content_title` <=> p.`content_title`
    AND a.`content_description` <=> p.`content_description`
    AND a.`topic` <=> p.`topic` AND a.`category` <=> p.`category`
    AND a.`tone` <=> p.`tone` AND a.`tone_sentiment` <=> p.`tone_sentiment`
    AND a.`event_type` <=> p.`event_type`
    AND a.`document_type_id` <=> p.`document_type_id`
    AND a.`document_type_name` <=> p.`document_type_name`
    AND a.`product_type` <=> p.`product_type`
    AND a.`article_status` <=> p.`article_status`
    AND a.`group_title` <=> p.`group_title` AND a.`news_type` <=> p.`news_type`
    AND a.`published_date` <=> p.`published_date`
    AND a.`vendor_indexed_time` <=> p.`vendor_indexed_time`
    AND a.`indexed_date_time` <=> p.`indexed_date_time`
    AND a.`last_updated` <=> p.`last_updated`
    AND a.`uploaded_by` <=> p.`uploaded_by`
    AND a.`last_updated_by` <=> p.`last_updated_by`
  ));

SELECT 'held_article_loaded' AS `check_name`, COUNT(*) AS `failure_count`
FROM `MSM_dataset_UAT`.`UAT_p4_holds` h
JOIN `MSM_dataset`.`articles` a ON a.`article_id` = h.`target_article_id`
WHERE h.`transform_id` = @transform_id;

WITH expected AS (
  SELECT `article_id`, `coverage_id`, `coverage_type`, `display_name`, `country`,
         `media_outlet_category`, `url`, COUNT(*) AS `row_count`
  FROM `MSM_dataset_UAT`.`UAT_p4_article_coverage`
  WHERE `transform_id` = @transform_id
  GROUP BY `article_id`, `coverage_id`, `coverage_type`, `display_name`, `country`,
           `media_outlet_category`, `url`
), actual AS (
  SELECT c.`article_id`, c.`coverage_id`, c.`coverage_type`, c.`display_name`, c.`country`,
         c.`media_outlet_category`, c.`url`, COUNT(*) AS `row_count`
  FROM `MSM_dataset`.`article_coverage` c
  JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p
    ON p.`article_id` = c.`article_id` AND p.`transform_id` = @transform_id
  GROUP BY c.`article_id`, c.`coverage_id`, c.`coverage_type`, c.`display_name`, c.`country`,
           c.`media_outlet_category`, c.`url`
), differences AS (
  SELECT e.`article_id`, e.`row_count` expected_count, COALESCE(a.`row_count`,0) actual_count
  FROM expected e LEFT JOIN actual a
    ON a.`article_id` = e.`article_id` AND a.`coverage_id` <=> e.`coverage_id`
   AND a.`coverage_type` <=> e.`coverage_type` AND a.`display_name` <=> e.`display_name`
   AND a.`country` <=> e.`country` AND a.`media_outlet_category` <=> e.`media_outlet_category`
   AND a.`url` <=> e.`url`
  UNION ALL
  SELECT a.`article_id`,0,a.`row_count` FROM actual a LEFT JOIN expected e
    ON e.`article_id` = a.`article_id` AND e.`coverage_id` <=> a.`coverage_id`
   AND e.`coverage_type` <=> a.`coverage_type` AND e.`display_name` <=> a.`display_name`
   AND e.`country` <=> a.`country` AND e.`media_outlet_category` <=> a.`media_outlet_category`
   AND e.`url` <=> a.`url` WHERE e.`article_id` IS NULL
)
SELECT 'coverage_multiset_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM differences WHERE expected_count <> actual_count;

WITH expected AS (
  SELECT `article_id`,`media_id`,`file_name`,`media_url`,`media_type`,`source`,COUNT(*) row_count
  FROM `MSM_dataset_UAT`.`UAT_p4_article_media` WHERE `transform_id`=@transform_id
  GROUP BY `article_id`,`media_id`,`file_name`,`media_url`,`media_type`,`source`
), actual AS (
  SELECT m.`article_id`,m.`media_id`,m.`file_name`,m.`media_url`,m.`media_type`,m.`source`,COUNT(*) row_count
  FROM `MSM_dataset`.`article_media` m JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p
    ON p.`article_id`=m.`article_id` AND p.`transform_id`=@transform_id
  GROUP BY m.`article_id`,m.`media_id`,m.`file_name`,m.`media_url`,m.`media_type`,m.`source`
), differences AS (
  SELECT e.`article_id`,e.row_count expected_count,COALESCE(a.row_count,0) actual_count
  FROM expected e LEFT JOIN actual a ON a.`article_id`=e.`article_id`
   AND a.`media_id` <=> e.`media_id` AND a.`file_name` <=> e.`file_name`
   AND a.`media_url` <=> e.`media_url` AND a.`media_type` <=> e.`media_type`
   AND a.`source` <=> e.`source`
  UNION ALL
  SELECT a.`article_id`,0,a.row_count FROM actual a LEFT JOIN expected e
    ON e.`article_id`=a.`article_id` AND e.`media_id` <=> a.`media_id`
   AND e.`file_name` <=> a.`file_name` AND e.`media_url` <=> a.`media_url`
   AND e.`media_type` <=> a.`media_type` AND e.`source` <=> a.`source`
  WHERE e.`article_id` IS NULL
)
SELECT 'media_multiset_mismatch' AS `check_name`,COUNT(*) AS `failure_count`
FROM differences WHERE expected_count<>actual_count;

WITH expected AS (
  SELECT `article_id`,`tag`,COUNT(*) row_count
  FROM `MSM_dataset_UAT`.`UAT_p4_article_tags` WHERE `transform_id`=@transform_id
  GROUP BY `article_id`,`tag`
), actual AS (
  SELECT t.`article_id`,t.`tag`,COUNT(*) row_count
  FROM `MSM_dataset`.`article_tags` t JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p
    ON p.`article_id`=t.`article_id` AND p.`transform_id`=@transform_id
  GROUP BY t.`article_id`,t.`tag`
), differences AS (
  SELECT e.`article_id`,e.row_count expected_count,COALESCE(a.row_count,0) actual_count
  FROM expected e LEFT JOIN actual a ON a.`article_id`=e.`article_id` AND a.`tag` <=> e.`tag`
  UNION ALL
  SELECT a.`article_id`,0,a.row_count FROM actual a LEFT JOIN expected e
    ON e.`article_id`=a.`article_id` AND e.`tag` <=> a.`tag` WHERE e.`article_id` IS NULL
)
SELECT 'tag_multiset_mismatch' AS `check_name`,COUNT(*) AS `failure_count`
FROM differences WHERE expected_count<>actual_count;

WITH expected AS (
  SELECT `article_id`,`user_group_id`,COUNT(*) row_count
  FROM `MSM_dataset_UAT`.`UAT_p4_article_user_groups` WHERE `transform_id`=@transform_id
  GROUP BY `article_id`,`user_group_id`
), actual AS (
  SELECT u.`article_id`,u.`user_group_id`,COUNT(*) row_count
  FROM `MSM_dataset`.`article_user_groups` u JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p
    ON p.`article_id`=u.`article_id` AND p.`transform_id`=@transform_id
  GROUP BY u.`article_id`,u.`user_group_id`
), differences AS (
  SELECT e.`article_id`,e.row_count expected_count,COALESCE(a.row_count,0) actual_count
  FROM expected e LEFT JOIN actual a ON a.`article_id`=e.`article_id`
   AND a.`user_group_id` <=> e.`user_group_id`
  UNION ALL
  SELECT a.`article_id`,0,a.row_count FROM actual a LEFT JOIN expected e
    ON e.`article_id`=a.`article_id` AND e.`user_group_id` <=> a.`user_group_id`
  WHERE e.`article_id` IS NULL
)
SELECT 'user_group_multiset_mismatch' AS `check_name`,COUNT(*) AS `failure_count`
FROM differences WHERE expected_count<>actual_count;

SELECT 'foreign_key_orphans' AS `check_name`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage` c LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=c.`article_id` WHERE a.`article_id` IS NULL)
 + (SELECT COUNT(*) FROM `MSM_dataset`.`article_media` m LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=m.`article_id` WHERE a.`article_id` IS NULL)
 + (SELECT COUNT(*) FROM `MSM_dataset`.`article_tags` t LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=t.`article_id` WHERE a.`article_id` IS NULL)
 + (SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups` u LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=u.`article_id` WHERE a.`article_id` IS NULL)
 AS `failure_count`;

SELECT 'coverage_view' AS `check_name`,COUNT(*) row_count,
       SUM(`total_coverage_count`) coverage_sum,SUM(`unique_outlets`) unique_outlet_sum
FROM `MSM_dataset`.`v_article_coverage_summary`;
SELECT 'outlet_daily_view' AS `check_name`,COUNT(*) row_count,SUM(`article_count`) article_count_sum,
       MIN(`publish_date`) first_date,MAX(`publish_date`) last_date
FROM `MSM_dataset`.`v_outlet_daily_volume`;

SELECT 'transaction_state' AS `check_name`,COUNT(*) AS `active_session_transactions`
FROM information_schema.innodb_trx WHERE `trx_mysql_thread_id`=CONNECTION_ID();
SELECT 'lock_state' AS `check_name`,IS_USED_LOCK('MSM_dataset_phase8_manual_cutover')=CONNECTION_ID() AS `lock_owned`;

-- If every failure_count is zero, the transaction count is 1, and lock_owned is 1,
-- the human operator may issue COMMIT and then SELECT RELEASE_LOCK(...).
-- Otherwise issue ROLLBACK and release the lock.
