-- Phase 8 MANUAL production rollback template.
-- SAFETY: defaults to NOT_APPROVED, refuses a partial/mismatched population,
-- and intentionally never COMMITs. Validate and commit manually in one session.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION TRANSACTION READ WRITE;
SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';
SET @phase8_rollback_confirmation = COALESCE(@phase8_rollback_confirmation, 'NOT_APPROVED');
-- In this same session, before sourcing this file, the human operator must issue:
-- SET @phase8_rollback_confirmation = 'APPROVED_MANUAL_ROLLBACK_8140';

SET @phase8_rollback_lock = GET_LOCK('MSM_dataset_phase8_manual_cutover',0);
SET @phase8_rollback_present = (
  SELECT COUNT(*) FROM `MSM_dataset`.`articles` a
  JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p ON p.`article_id`=a.`article_id`
  WHERE p.`transform_id`=@transform_id
);
SET @phase8_rollback_field_mismatches = (
  SELECT COUNT(*)
  FROM `MSM_dataset_UAT`.`UAT_p4_articles` p LEFT JOIN `MSM_dataset`.`articles` a
    ON a.`article_id`=p.`article_id`
  WHERE p.`transform_id`=@transform_id AND (a.`article_id` IS NULL OR NOT (
    a.`document_id` <=> p.`document_id` AND a.`vendor_article_id` <=> p.`vendor_article_id`
    AND a.`article_title` <=> p.`article_title` AND a.`content_title` <=> p.`content_title`
    AND a.`content_description` <=> p.`content_description` AND a.`topic` <=> p.`topic`
    AND a.`category` <=> p.`category` AND a.`tone` <=> p.`tone`
    AND a.`tone_sentiment` <=> p.`tone_sentiment` AND a.`event_type` <=> p.`event_type`
    AND a.`document_type_id` <=> p.`document_type_id`
    AND a.`document_type_name` <=> p.`document_type_name`
    AND a.`product_type` <=> p.`product_type` AND a.`article_status` <=> p.`article_status`
    AND a.`group_title` <=> p.`group_title` AND a.`news_type` <=> p.`news_type`
    AND a.`published_date` <=> p.`published_date`
    AND a.`vendor_indexed_time` <=> p.`vendor_indexed_time`
    AND a.`indexed_date_time` <=> p.`indexed_date_time` AND a.`last_updated` <=> p.`last_updated`
    AND a.`uploaded_by` <=> p.`uploaded_by` AND a.`last_updated_by` <=> p.`last_updated_by`
  ))
);
SET @phase8_rollback_gate_failures =
    (@phase8_rollback_confirmation <> 'APPROVED_MANUAL_ROLLBACK_8140')
  + (@phase8_rollback_lock <> 1)
  + (@phase8_rollback_present <> 8140)
  + @phase8_rollback_field_mismatches;

SELECT 'rollback_gate' AS `check_name`,@phase8_rollback_gate_failures AS `failure_count`,
       @phase8_rollback_present AS `matching_articles`,
       @phase8_rollback_field_mismatches AS `field_mismatches`;

SET @phase8_rb_before_articles=(SELECT COUNT(*) FROM `MSM_dataset`.`articles`);
SET @phase8_rb_before_coverage=(SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage`);
SET @phase8_rb_before_media=(SELECT COUNT(*) FROM `MSM_dataset`.`article_media`);
SET @phase8_rb_before_tags=(SELECT COUNT(*) FROM `MSM_dataset`.`article_tags`);
SET @phase8_rb_before_user_groups=(SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups`);

START TRANSACTION;
DELETE a FROM `MSM_dataset`.`articles` a
JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p ON p.`article_id`=a.`article_id`
WHERE p.`transform_id`=@transform_id AND @phase8_rollback_gate_failures=0;
SET @phase8_deleted_articles=ROW_COUNT();

SELECT 'rollback_delete_count_mismatch' AS `check_name`,
       @phase8_deleted_articles <> 8140 AS `failure_count`;
SELECT 'rollback_candidate_ids_remaining' AS `check_name`,COUNT(*) AS `failure_count`
FROM `MSM_dataset`.`articles` a JOIN `MSM_dataset_UAT`.`UAT_p4_articles` p
  ON p.`article_id`=a.`article_id` AND p.`transform_id`=@transform_id;
SELECT 'rollback_total_mismatch' AS `check_name`,
  ((SELECT COUNT(*) FROM `MSM_dataset`.`articles`) <> @phase8_rb_before_articles-8140)
 + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage`) <> @phase8_rb_before_coverage-8140)
 + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_media`) <> @phase8_rb_before_media-343)
 + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_tags`) <> @phase8_rb_before_tags-227222)
 + ((SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups`) <> @phase8_rb_before_user_groups-8140)
 AS `failure_count`;
SELECT 'rollback_foreign_key_orphans' AS `check_name`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage` c LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=c.`article_id` WHERE a.`article_id` IS NULL)
 + (SELECT COUNT(*) FROM `MSM_dataset`.`article_media` m LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=m.`article_id` WHERE a.`article_id` IS NULL)
 + (SELECT COUNT(*) FROM `MSM_dataset`.`article_tags` t LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=t.`article_id` WHERE a.`article_id` IS NULL)
 + (SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups` u LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id`=u.`article_id` WHERE a.`article_id` IS NULL)
 AS `failure_count`;
SELECT 'rollback_transaction_state' AS `check_name`,COUNT(*) AS `active_session_transactions`
FROM information_schema.innodb_trx WHERE `trx_mysql_thread_id`=CONNECTION_ID();

-- Commit manually only if every failure_count is zero and transaction count is 1.
-- Otherwise ROLLBACK. Then release the named lock.
