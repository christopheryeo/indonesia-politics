-- Validate the uncommitted Phase 7 rollback in the same session.

SELECT 'rollback_count_mismatch' AS `check_name`,
  (@phase7_deleted_articles <> 8140)
  + ((SELECT COUNT(*) FROM `UAT_articles`) <> 13789)
  + ((SELECT COUNT(*) FROM `UAT_article_coverage`) <> 27355)
  + ((SELECT COUNT(*) FROM `UAT_article_media`) <> 420)
  + ((SELECT COUNT(*) FROM `UAT_article_tags`) <> 224501)
  + ((SELECT COUNT(*) FROM `UAT_article_user_groups`) <> 9287)
  AS `failure_count`;

SELECT 'manifest_ids_still_present' AS `check_name`, COUNT(*) AS `failure_count`
FROM `phase7_loaded_article_ids` m
JOIN `UAT_articles` a ON a.`article_id` = m.`article_id`;

SELECT 'foreign_key_orphans' AS `check_name`,
  (SELECT COUNT(*) FROM `UAT_article_coverage` c LEFT JOIN `UAT_articles` a ON a.`article_id` = c.`article_id` WHERE a.`article_id` IS NULL)
  + (SELECT COUNT(*) FROM `UAT_article_media` m LEFT JOIN `UAT_articles` a ON a.`article_id` = m.`article_id` WHERE a.`article_id` IS NULL)
  + (SELECT COUNT(*) FROM `UAT_article_tags` t LEFT JOIN `UAT_articles` a ON a.`article_id` = t.`article_id` WHERE a.`article_id` IS NULL)
  + (SELECT COUNT(*) FROM `UAT_article_user_groups` u LEFT JOIN `UAT_articles` a ON a.`article_id` = u.`article_id` WHERE a.`article_id` IS NULL)
  AS `failure_count`;

SELECT 'coverage_view' AS `check_name`, COUNT(*) AS `row_count`,
       SUM(`total_coverage_count`) AS `coverage_sum`,
       SUM(`unique_outlets`) AS `unique_outlet_sum`
FROM `UAT_v_article_coverage_summary`;

SELECT 'outlet_view' AS `check_name`, COUNT(*) AS `row_count`,
       SUM(`article_count`) AS `article_count_sum`,
       MIN(`publish_date`) AS `first_date`, MAX(`publish_date`) AS `last_date`
FROM `UAT_v_outlet_daily_volume`;

SELECT 'transaction_state' AS `check_name`, COUNT(*) AS `active_session_transactions`
FROM information_schema.innodb_trx
WHERE `trx_mysql_thread_id` = CONNECTION_ID();
