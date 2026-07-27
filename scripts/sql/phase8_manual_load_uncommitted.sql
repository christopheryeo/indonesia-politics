-- Phase 8 MANUAL production load template.
-- SAFETY: this script intentionally defaults to NOT_APPROVED and never COMMITs.
-- Run only after the read-only preflight, a fresh production backup, an approved
-- maintenance window, and explicit operator sign-off. Validate in the SAME session.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET SESSION TRANSACTION READ WRITE;
SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';
SET @phase8_operator_confirmation = COALESCE(@phase8_operator_confirmation, 'NOT_APPROVED');
-- In this same session, before sourcing this file, the human operator must issue:
-- SET @phase8_operator_confirmation = 'APPROVED_MANUAL_CUTOVER_8140';

SET @phase8_lock = GET_LOCK('MSM_dataset_phase8_manual_cutover', 0);
SET @phase8_source_gate = (
  SELECT (COUNT(*) = 1)
  FROM `MSM_dataset_UAT`.`UAT_p4_transform_batches`
  WHERE `transform_id` = @transform_id AND `status` = 'validated'
);
SET @phase8_source_count_gate = (
  SELECT COUNT(*) = 8140 FROM `MSM_dataset_UAT`.`UAT_p4_articles`
  WHERE `transform_id` = @transform_id
);
SET @phase8_target_collisions = (
  SELECT COUNT(*)
  FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
  JOIN `MSM_dataset`.`articles` a ON a.`article_id` = p.`article_id`
  WHERE p.`transform_id` = @transform_id
);
SET @phase8_vendor_collisions = (
  SELECT COUNT(DISTINCT p.`article_id`)
  FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
  JOIN `MSM_dataset`.`articles` a ON a.`vendor_article_id` = p.`vendor_article_id`
  WHERE p.`transform_id` = @transform_id AND p.`vendor_article_id` IS NOT NULL
);
SET @phase8_gate_failures =
    (@phase8_operator_confirmation <> 'APPROVED_MANUAL_CUTOVER_8140')
  + (@phase8_lock <> 1)
  + (@phase8_source_gate <> 1)
  + (@phase8_source_count_gate <> 1)
  + @phase8_target_collisions
  + @phase8_vendor_collisions;

SELECT 'load_gate' AS `check_name`, @phase8_gate_failures AS `failure_count`,
       @phase8_lock AS `lock_acquired`, @phase8_target_collisions AS `article_id_collisions`,
       @phase8_vendor_collisions AS `vendor_id_collisions`;

SET @phase8_before_articles = (SELECT COUNT(*) FROM `MSM_dataset`.`articles`);
SET @phase8_before_coverage = (SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage`);
SET @phase8_before_media = (SELECT COUNT(*) FROM `MSM_dataset`.`article_media`);
SET @phase8_before_tags = (SELECT COUNT(*) FROM `MSM_dataset`.`article_tags`);
SET @phase8_before_user_groups = (SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups`);

START TRANSACTION;

INSERT INTO `MSM_dataset`.`articles` (
  `article_id`, `document_id`, `vendor_article_id`, `article_title`, `content_title`,
  `content_description`, `topic`, `category`, `tone`, `tone_sentiment`, `event_type`,
  `document_type_id`, `document_type_name`, `product_type`, `article_status`,
  `group_title`, `news_type`, `published_date`, `vendor_indexed_time`,
  `indexed_date_time`, `last_updated`, `uploaded_by`, `last_updated_by`
)
SELECT
  p.`article_id`, p.`document_id`, p.`vendor_article_id`, p.`article_title`, p.`content_title`,
  p.`content_description`, p.`topic`, p.`category`, p.`tone`, p.`tone_sentiment`, p.`event_type`,
  p.`document_type_id`, p.`document_type_name`, p.`product_type`, p.`article_status`,
  p.`group_title`, p.`news_type`, p.`published_date`, p.`vendor_indexed_time`,
  p.`indexed_date_time`, p.`last_updated`, p.`uploaded_by`, p.`last_updated_by`
FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
WHERE p.`transform_id` = @transform_id AND @phase8_gate_failures = 0
ORDER BY p.`article_id`;
SET @phase8_inserted_articles = ROW_COUNT();

INSERT INTO `MSM_dataset`.`article_coverage` (
  `article_id`, `coverage_id`, `coverage_type`, `display_name`, `country`,
  `media_outlet_category`, `url`
)
SELECT c.`article_id`, c.`coverage_id`, c.`coverage_type`, c.`display_name`, c.`country`,
       c.`media_outlet_category`, c.`url`
FROM `MSM_dataset_UAT`.`UAT_p4_article_coverage` c
WHERE c.`transform_id` = @transform_id AND @phase8_gate_failures = 0
ORDER BY c.`article_id`, c.`coverage_type`, c.`source_ordinal`;
SET @phase8_inserted_coverage = ROW_COUNT();

INSERT INTO `MSM_dataset`.`article_media` (
  `article_id`, `media_id`, `file_name`, `media_url`, `media_type`, `source`
)
SELECT m.`article_id`, m.`media_id`, m.`file_name`, m.`media_url`, m.`media_type`, m.`source`
FROM `MSM_dataset_UAT`.`UAT_p4_article_media` m
WHERE m.`transform_id` = @transform_id AND @phase8_gate_failures = 0
ORDER BY m.`article_id`, m.`source_ordinal`;
SET @phase8_inserted_media = ROW_COUNT();

INSERT INTO `MSM_dataset`.`article_tags` (`article_id`, `tag`)
SELECT t.`article_id`, t.`tag`
FROM `MSM_dataset_UAT`.`UAT_p4_article_tags` t
WHERE t.`transform_id` = @transform_id AND @phase8_gate_failures = 0
ORDER BY t.`article_id`, t.`source_ordinal`;
SET @phase8_inserted_tags = ROW_COUNT();

INSERT INTO `MSM_dataset`.`article_user_groups` (`article_id`, `user_group_id`)
SELECT u.`article_id`, u.`user_group_id`
FROM `MSM_dataset_UAT`.`UAT_p4_article_user_groups` u
WHERE u.`transform_id` = @transform_id AND @phase8_gate_failures = 0
ORDER BY u.`article_id`, u.`source_ordinal`;
SET @phase8_inserted_user_groups = ROW_COUNT();

SELECT 'uncommitted_insert_counts' AS `check_name`,
       @phase8_inserted_articles AS `articles`, @phase8_inserted_coverage AS `coverage`,
       @phase8_inserted_media AS `media`, @phase8_inserted_tags AS `tags`,
       @phase8_inserted_user_groups AS `user_groups`;

-- DO NOT COMMIT HERE. Run phase8_manual_validate_uncommitted.sql in this session.
