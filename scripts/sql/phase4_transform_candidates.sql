-- Phase 4 deterministic transformation for MSM_dataset_UAT.
-- Requires a validated Phase 3 batch and writes only to UAT_p4_* tables.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION group_concat_max_len = 65535;
USE `MSM_dataset_UAT`;

SET @source_batch_id = 'c53d2b3f-6d07-534c-abb2-00011d79d67a';
SET @transform_id = UUID();
SET @transform_version = 'phase4-transform.v1';
SET @allocation_ceiling = GREATEST(
  (SELECT COALESCE(MAX(`article_id`), 0) FROM `UAT_articles`),
  (SELECT COALESCE(MAX(`source_article_id`), 0)
     FROM `UAT_stg_articles`
    WHERE `batch_id` = @source_batch_id)
);

START TRANSACTION;

-- This INSERT deliberately selects only a validated Phase 3 batch. If the gate
-- is not satisfied, the subsequent identity INSERT fails on its parent FK.
INSERT INTO `UAT_p4_transform_batches` (
  `transform_id`, `source_batch_id`, `transform_version`, `status`,
  `allocation_ceiling`, `source_article_count`, `started_at`, `notes`
)
SELECT
  @transform_id,
  b.`batch_id`,
  @transform_version,
  'building',
  @allocation_ceiling,
  b.`actual_article_count`,
  UTC_TIMESTAMP(6),
  'Phase 4 UAT-only identity resolution and canonical-shaped candidate materialisation'
FROM `UAT_stg_import_batches` b
WHERE b.`batch_id` = @source_batch_id
  AND b.`status` = 'validated';

INSERT INTO `UAT_p4_article_identity` (
  `transform_id`, `source_batch_id`, `staging_article_id`, `source_article_id`,
  `target_article_id`, `identity_action`, `disposition`,
  `blocking_issue_count`, `warning_issue_count`, `source_record_hash`
)
WITH issue_counts AS (
  SELECT
    q.`batch_id`,
    q.`staging_article_id`,
    SUM(
      q.`rule_code` <> 'PRIMARY_KEY_COLLISION'
      AND (
        (q.`severity` = 'error' AND q.`review_status` IN ('pending','rejected'))
        OR q.`review_status` = 'rejected'
      )
    ) AS `blocking_issue_count`,
    SUM(
      q.`rule_code` <> 'PRIMARY_KEY_COLLISION'
      AND q.`severity` = 'warning'
      AND q.`review_status` = 'pending'
    ) AS `warning_issue_count`
  FROM `UAT_stg_quarantine` q
  WHERE q.`batch_id` = @source_batch_id
  GROUP BY q.`batch_id`, q.`staging_article_id`
), collision_ranks AS (
  SELECT
    a.`staging_article_id`,
    ROW_NUMBER() OVER (
      ORDER BY a.`source_article_id`, a.`staging_article_id`
    ) AS `collision_rank`
  FROM `UAT_stg_articles` a
  WHERE a.`batch_id` = @source_batch_id
    AND EXISTS (
      SELECT 1
      FROM `UAT_articles` u
      WHERE u.`article_id` = a.`source_article_id`
    )
)
SELECT
  @transform_id,
  a.`batch_id`,
  a.`staging_article_id`,
  a.`source_article_id`,
  CASE
    WHEN cr.`collision_rank` IS NULL THEN a.`source_article_id`
    ELSE @allocation_ceiling + cr.`collision_rank`
  END AS `target_article_id`,
  CASE
    WHEN cr.`collision_rank` IS NULL THEN 'preserved'
    ELSE 'remapped_collision'
  END AS `identity_action`,
  CASE
    WHEN COALESCE(i.`blocking_issue_count`, 0) > 0 THEN 'quarantined'
    WHEN COALESCE(i.`warning_issue_count`, 0) > 0 THEN 'review'
    ELSE 'candidate'
  END AS `disposition`,
  COALESCE(i.`blocking_issue_count`, 0),
  COALESCE(i.`warning_issue_count`, 0),
  a.`record_hash`
FROM `UAT_stg_articles` a
LEFT JOIN issue_counts i
  ON i.`batch_id` = a.`batch_id`
 AND i.`staging_article_id` = a.`staging_article_id`
LEFT JOIN collision_ranks cr
  ON cr.`staging_article_id` = a.`staging_article_id`
WHERE a.`batch_id` = @source_batch_id;

INSERT INTO `UAT_p4_articles` (
  `transform_id`, `source_batch_id`, `staging_article_id`, `source_article_id`,
  `article_id`, `document_id`, `vendor_article_id`, `article_title`, `content_title`,
  `content_description`, `topic`, `category`, `tone`, `tone_sentiment`, `event_type`,
  `document_type_id`, `document_type_name`, `product_type`, `article_status`,
  `group_title`, `news_type`, `published_date`, `vendor_indexed_time`,
  `indexed_date_time`, `last_updated`, `uploaded_by`, `last_updated_by`,
  `source_record_hash`
)
SELECT
  i.`transform_id`, a.`batch_id`, a.`staging_article_id`, a.`source_article_id`,
  i.`target_article_id`, a.`document_id`, a.`vendor_article_id`, a.`article_title`,
  a.`content_title`, a.`content_description`, a.`topic`, a.`category`, a.`tone`,
  a.`tone_sentiment`, a.`event_type`, a.`document_type_id`, a.`document_type_name`,
  a.`product_type`, a.`article_status`, a.`group_title`, a.`news_type`,
  a.`published_date`, a.`vendor_indexed_time`, a.`indexed_date_time`, a.`last_updated`,
  a.`uploaded_by`, a.`last_updated_by`, a.`record_hash`
FROM `UAT_p4_article_identity` i
JOIN `UAT_stg_articles` a
  ON a.`batch_id` = i.`source_batch_id`
 AND a.`staging_article_id` = i.`staging_article_id`
WHERE i.`transform_id` = @transform_id
  AND i.`disposition` = 'candidate';

INSERT INTO `UAT_p4_article_coverage` (
  `transform_id`, `article_id`, `source_ordinal`, `coverage_id`, `coverage_type`,
  `display_name`, `country`, `media_outlet_category`, `url`, `source_record_hash`
)
SELECT
  p.`transform_id`, p.`article_id`, c.`source_ordinal`, c.`coverage_id`, c.`coverage_type`,
  c.`display_name`, c.`country`, c.`media_outlet_category`, c.`url`, c.`record_hash`
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_coverage` c
  ON c.`batch_id` = p.`source_batch_id`
 AND c.`staging_article_id` = p.`staging_article_id`
WHERE p.`transform_id` = @transform_id;

INSERT INTO `UAT_p4_article_media` (
  `transform_id`, `article_id`, `source_ordinal`, `media_id`, `file_name`,
  `media_url`, `media_type`, `source`, `source_record_hash`
)
SELECT
  p.`transform_id`, p.`article_id`, m.`source_ordinal`, m.`media_id`, m.`file_name`,
  m.`media_url`, m.`media_type`, m.`source`, m.`record_hash`
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_media` m
  ON m.`batch_id` = p.`source_batch_id`
 AND m.`staging_article_id` = p.`staging_article_id`
WHERE p.`transform_id` = @transform_id;

INSERT INTO `UAT_p4_article_tags` (
  `transform_id`, `article_id`, `source_ordinal`, `tag`, `source_record_hash`
)
SELECT
  p.`transform_id`, p.`article_id`, t.`source_ordinal`, t.`tag`, t.`record_hash`
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_tags` t
  ON t.`batch_id` = p.`source_batch_id`
 AND t.`staging_article_id` = p.`staging_article_id`
WHERE p.`transform_id` = @transform_id;

INSERT INTO `UAT_p4_article_user_groups` (
  `transform_id`, `article_id`, `source_ordinal`, `user_group_id`, `source_record_hash`
)
SELECT
  p.`transform_id`, p.`article_id`, u.`source_ordinal`, u.`user_group_id`, u.`record_hash`
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_user_groups` u
  ON u.`batch_id` = p.`source_batch_id`
 AND u.`staging_article_id` = p.`staging_article_id`
WHERE p.`transform_id` = @transform_id;

INSERT INTO `UAT_p4_holds` (
  `transform_id`, `source_batch_id`, `staging_article_id`, `source_article_id`,
  `target_article_id`, `disposition`, `blocking_issue_count`, `warning_issue_count`,
  `rule_codes`, `source_record_hash`
)
SELECT
  i.`transform_id`, i.`source_batch_id`, i.`staging_article_id`, i.`source_article_id`,
  i.`target_article_id`, i.`disposition`, i.`blocking_issue_count`, i.`warning_issue_count`,
  GROUP_CONCAT(DISTINCT q.`rule_code` ORDER BY q.`rule_code` SEPARATOR ','),
  i.`source_record_hash`
FROM `UAT_p4_article_identity` i
JOIN `UAT_stg_quarantine` q
  ON q.`batch_id` = i.`source_batch_id`
 AND q.`staging_article_id` = i.`staging_article_id`
 AND q.`rule_code` <> 'PRIMARY_KEY_COLLISION'
WHERE i.`transform_id` = @transform_id
  AND i.`disposition` IN ('review','quarantined')
GROUP BY
  i.`transform_id`, i.`source_batch_id`, i.`staging_article_id`, i.`source_article_id`,
  i.`target_article_id`, i.`disposition`, i.`blocking_issue_count`, i.`warning_issue_count`,
  i.`source_record_hash`;

UPDATE `UAT_p4_transform_batches`
SET
  `status` = 'built',
  `candidate_article_count` = (
    SELECT COUNT(*) FROM `UAT_p4_articles` WHERE `transform_id` = @transform_id
  ),
  `review_article_count` = (
    SELECT COUNT(*) FROM `UAT_p4_article_identity`
     WHERE `transform_id` = @transform_id AND `disposition` = 'review'
  ),
  `quarantined_article_count` = (
    SELECT COUNT(*) FROM `UAT_p4_article_identity`
     WHERE `transform_id` = @transform_id AND `disposition` = 'quarantined'
  ),
  `candidate_coverage_count` = (
    SELECT COUNT(*) FROM `UAT_p4_article_coverage` WHERE `transform_id` = @transform_id
  ),
  `candidate_media_count` = (
    SELECT COUNT(*) FROM `UAT_p4_article_media` WHERE `transform_id` = @transform_id
  ),
  `candidate_tag_count` = (
    SELECT COUNT(*) FROM `UAT_p4_article_tags` WHERE `transform_id` = @transform_id
  ),
  `candidate_user_group_count` = (
    SELECT COUNT(*) FROM `UAT_p4_article_user_groups` WHERE `transform_id` = @transform_id
  ),
  `built_at` = UTC_TIMESTAMP(6)
WHERE `transform_id` = @transform_id;

COMMIT;

SELECT @transform_id AS `transform_id`;
