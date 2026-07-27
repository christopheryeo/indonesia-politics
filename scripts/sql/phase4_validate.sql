-- Repeatable Phase 4 validation for MSM_dataset_UAT.
-- Read-only except for the final status update, which must be run separately
-- only after every result in this script passes.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
USE `MSM_dataset_UAT`;

SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';
SET @source_batch_id = 'c53d2b3f-6d07-534c-abb2-00011d79d67a';

SELECT 'registry' AS `check_name`, b.*
FROM `UAT_p4_transform_batches` b
WHERE b.`transform_id` = @transform_id;

SELECT 'identity_action' AS `check_name`, `identity_action`, COUNT(*) AS `row_count`
FROM `UAT_p4_article_identity`
WHERE `transform_id` = @transform_id
GROUP BY `identity_action`
ORDER BY `identity_action`;

SELECT 'disposition' AS `check_name`, `disposition`, COUNT(*) AS `row_count`
FROM `UAT_p4_article_identity`
WHERE `transform_id` = @transform_id
GROUP BY `disposition`
ORDER BY `disposition`;

SELECT 'candidate_counts' AS `check_name`,
  (SELECT COUNT(*) FROM `UAT_p4_articles` WHERE `transform_id` = @transform_id) AS `articles`,
  (SELECT COUNT(*) FROM `UAT_p4_article_coverage` WHERE `transform_id` = @transform_id) AS `coverage`,
  (SELECT COUNT(*) FROM `UAT_p4_article_media` WHERE `transform_id` = @transform_id) AS `media`,
  (SELECT COUNT(*) FROM `UAT_p4_article_tags` WHERE `transform_id` = @transform_id) AS `tags`,
  (SELECT COUNT(*) FROM `UAT_p4_article_user_groups` WHERE `transform_id` = @transform_id) AS `user_groups`,
  (SELECT COUNT(*) FROM `UAT_p4_holds` WHERE `transform_id` = @transform_id) AS `holds`;

SELECT 'identity_source_missing' AS `check_name`, COUNT(*) AS `failure_count`
FROM `UAT_stg_articles` a
LEFT JOIN `UAT_p4_article_identity` i
  ON i.`source_batch_id` = a.`batch_id`
 AND i.`staging_article_id` = a.`staging_article_id`
 AND i.`transform_id` = @transform_id
WHERE a.`batch_id` = @source_batch_id
  AND i.`staging_article_id` IS NULL
UNION ALL
SELECT 'identity_extra', COUNT(*)
FROM `UAT_p4_article_identity` i
LEFT JOIN `UAT_stg_articles` a
  ON a.`batch_id` = i.`source_batch_id`
 AND a.`staging_article_id` = i.`staging_article_id`
WHERE i.`transform_id` = @transform_id
  AND a.`staging_article_id` IS NULL
UNION ALL
SELECT 'target_collides_with_canonical', COUNT(*)
FROM `UAT_p4_article_identity` i
JOIN `UAT_articles` u ON u.`article_id` = i.`target_article_id`
WHERE i.`transform_id` = @transform_id
UNION ALL
SELECT 'preserved_identity_mismatch', COUNT(*)
FROM `UAT_p4_article_identity` i
WHERE i.`transform_id` = @transform_id
  AND i.`identity_action` = 'preserved'
  AND i.`target_article_id` <> i.`source_article_id`;

WITH collision_ranks AS (
  SELECT
    a.`staging_article_id`,
    ROW_NUMBER() OVER (ORDER BY a.`source_article_id`, a.`staging_article_id`) AS `collision_rank`
  FROM `UAT_stg_articles` a
  WHERE a.`batch_id` = @source_batch_id
    AND EXISTS (
      SELECT 1 FROM `UAT_articles` u WHERE u.`article_id` = a.`source_article_id`
    )
)
SELECT 'remapped_identity_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM `UAT_p4_article_identity` i
JOIN collision_ranks c ON c.`staging_article_id` = i.`staging_article_id`
JOIN `UAT_p4_transform_batches` b ON b.`transform_id` = i.`transform_id`
WHERE i.`transform_id` = @transform_id
  AND (
    i.`identity_action` <> 'remapped_collision'
    OR i.`target_article_id` <> b.`allocation_ceiling` + c.`collision_rank`
  );

WITH issue_counts AS (
  SELECT
    q.`batch_id`, q.`staging_article_id`,
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
)
SELECT 'disposition_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM `UAT_p4_article_identity` i
LEFT JOIN issue_counts q
  ON q.`batch_id` = i.`source_batch_id`
 AND q.`staging_article_id` = i.`staging_article_id`
WHERE i.`transform_id` = @transform_id
  AND i.`disposition` <> CASE
    WHEN COALESCE(q.`blocking_issue_count`, 0) > 0 THEN 'quarantined'
    WHEN COALESCE(q.`warning_issue_count`, 0) > 0 THEN 'review'
    ELSE 'candidate'
  END;

SELECT 'candidate_article_missing_or_extra' AS `check_name`,
  SUM(i.`disposition` = 'candidate' AND p.`article_id` IS NULL)
  + SUM(i.`disposition` <> 'candidate' AND p.`article_id` IS NOT NULL) AS `failure_count`
FROM `UAT_p4_article_identity` i
LEFT JOIN `UAT_p4_articles` p
  ON p.`transform_id` = i.`transform_id`
 AND p.`staging_article_id` = i.`staging_article_id`
WHERE i.`transform_id` = @transform_id;

SELECT 'article_field_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM `UAT_p4_articles` p
JOIN `UAT_stg_articles` a
  ON a.`batch_id` = p.`source_batch_id`
 AND a.`staging_article_id` = p.`staging_article_id`
WHERE p.`transform_id` = @transform_id
  AND NOT (
    p.`source_article_id` <=> a.`source_article_id`
    AND p.`document_id` <=> a.`document_id`
    AND p.`vendor_article_id` <=> a.`vendor_article_id`
    AND p.`article_title` <=> a.`article_title`
    AND p.`content_title` <=> a.`content_title`
    AND p.`content_description` <=> a.`content_description`
    AND p.`topic` <=> a.`topic`
    AND p.`category` <=> a.`category`
    AND p.`tone` <=> a.`tone`
    AND p.`tone_sentiment` <=> a.`tone_sentiment`
    AND p.`event_type` <=> a.`event_type`
    AND p.`document_type_id` <=> a.`document_type_id`
    AND p.`document_type_name` <=> a.`document_type_name`
    AND p.`product_type` <=> a.`product_type`
    AND p.`article_status` <=> a.`article_status`
    AND p.`group_title` <=> a.`group_title`
    AND p.`news_type` <=> a.`news_type`
    AND p.`published_date` <=> a.`published_date`
    AND p.`vendor_indexed_time` <=> a.`vendor_indexed_time`
    AND p.`indexed_date_time` <=> a.`indexed_date_time`
    AND p.`last_updated` <=> a.`last_updated`
    AND p.`uploaded_by` <=> a.`uploaded_by`
    AND p.`last_updated_by` <=> a.`last_updated_by`
    AND p.`source_record_hash` <=> a.`record_hash`
  );

SELECT 'coverage_missing_or_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_coverage` s
  ON s.`batch_id` = p.`source_batch_id`
 AND s.`staging_article_id` = p.`staging_article_id`
LEFT JOIN `UAT_p4_article_coverage` c
  ON c.`transform_id` = p.`transform_id`
 AND c.`article_id` = p.`article_id`
 AND c.`coverage_type` = s.`coverage_type`
 AND c.`source_ordinal` = s.`source_ordinal`
WHERE p.`transform_id` = @transform_id
  AND (
    c.`article_id` IS NULL
    OR NOT (
      c.`coverage_id` <=> s.`coverage_id`
      AND c.`display_name` <=> s.`display_name`
      AND c.`country` <=> s.`country`
      AND c.`media_outlet_category` <=> s.`media_outlet_category`
      AND c.`url` <=> s.`url`
      AND c.`source_record_hash` <=> s.`record_hash`
    )
  )
UNION ALL
SELECT 'media_missing_or_mismatch', COUNT(*)
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_media` s
  ON s.`batch_id` = p.`source_batch_id`
 AND s.`staging_article_id` = p.`staging_article_id`
LEFT JOIN `UAT_p4_article_media` m
  ON m.`transform_id` = p.`transform_id`
 AND m.`article_id` = p.`article_id`
 AND m.`source_ordinal` = s.`source_ordinal`
WHERE p.`transform_id` = @transform_id
  AND (
    m.`article_id` IS NULL
    OR NOT (
      m.`media_id` <=> s.`media_id`
      AND m.`file_name` <=> s.`file_name`
      AND m.`media_url` <=> s.`media_url`
      AND m.`media_type` <=> s.`media_type`
      AND m.`source` <=> s.`source`
      AND m.`source_record_hash` <=> s.`record_hash`
    )
  )
UNION ALL
SELECT 'tag_missing_or_mismatch', COUNT(*)
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_tags` s
  ON s.`batch_id` = p.`source_batch_id`
 AND s.`staging_article_id` = p.`staging_article_id`
LEFT JOIN `UAT_p4_article_tags` t
  ON t.`transform_id` = p.`transform_id`
 AND t.`article_id` = p.`article_id`
 AND t.`source_ordinal` = s.`source_ordinal`
WHERE p.`transform_id` = @transform_id
  AND (
    t.`article_id` IS NULL
    OR NOT (t.`tag` <=> s.`tag` AND t.`source_record_hash` <=> s.`record_hash`)
  )
UNION ALL
SELECT 'user_group_missing_or_mismatch', COUNT(*)
FROM `UAT_p4_articles` p
JOIN `UAT_stg_article_user_groups` s
  ON s.`batch_id` = p.`source_batch_id`
 AND s.`staging_article_id` = p.`staging_article_id`
LEFT JOIN `UAT_p4_article_user_groups` u
  ON u.`transform_id` = p.`transform_id`
 AND u.`article_id` = p.`article_id`
 AND u.`source_ordinal` = s.`source_ordinal`
WHERE p.`transform_id` = @transform_id
  AND (
    u.`article_id` IS NULL
    OR NOT (
      u.`user_group_id` <=> s.`user_group_id`
      AND u.`source_record_hash` <=> s.`record_hash`
    )
  );

SELECT 'extra_candidate_children' AS `check_name`,
  (SELECT COUNT(*)
     FROM `UAT_p4_article_coverage` c
     LEFT JOIN `UAT_p4_articles` p
       ON p.`transform_id` = c.`transform_id` AND p.`article_id` = c.`article_id`
    WHERE c.`transform_id` = @transform_id AND p.`article_id` IS NULL)
  +
  (SELECT COUNT(*)
     FROM `UAT_p4_article_media` m
     LEFT JOIN `UAT_p4_articles` p
       ON p.`transform_id` = m.`transform_id` AND p.`article_id` = m.`article_id`
    WHERE m.`transform_id` = @transform_id AND p.`article_id` IS NULL)
  +
  (SELECT COUNT(*)
     FROM `UAT_p4_article_tags` t
     LEFT JOIN `UAT_p4_articles` p
       ON p.`transform_id` = t.`transform_id` AND p.`article_id` = t.`article_id`
    WHERE t.`transform_id` = @transform_id AND p.`article_id` IS NULL)
  +
  (SELECT COUNT(*)
     FROM `UAT_p4_article_user_groups` u
     LEFT JOIN `UAT_p4_articles` p
       ON p.`transform_id` = u.`transform_id` AND p.`article_id` = u.`article_id`
    WHERE u.`transform_id` = @transform_id AND p.`article_id` IS NULL)
  AS `failure_count`;

SELECT 'held_rule' AS `check_name`, h.`disposition`, q.`rule_code`, q.`severity`,
       COUNT(DISTINCT h.`staging_article_id`) AS `affected_articles`
FROM `UAT_p4_holds` h
JOIN `UAT_stg_quarantine` q
  ON q.`batch_id` = h.`source_batch_id`
 AND q.`staging_article_id` = h.`staging_article_id`
 AND q.`rule_code` <> 'PRIMARY_KEY_COLLISION'
WHERE h.`transform_id` = @transform_id
GROUP BY h.`disposition`, q.`rule_code`, q.`severity`
ORDER BY h.`disposition`, q.`severity`, q.`rule_code`;

SELECT 'common_target_schema_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM information_schema.columns c
JOIN information_schema.columns p
  ON p.`table_schema` = c.`table_schema`
 AND p.`column_name` = c.`column_name`
 AND p.`table_name` = CONCAT('UAT_p4_', SUBSTRING(c.`table_name`, 5))
WHERE c.`table_schema` = 'MSM_dataset_UAT'
  AND c.`table_name` IN (
    'UAT_articles', 'UAT_article_coverage', 'UAT_article_media',
    'UAT_article_tags', 'UAT_article_user_groups'
  )
  AND c.`column_name` <> 'id'
  AND NOT (
    c.`column_type` <=> p.`column_type`
    AND c.`is_nullable` <=> p.`is_nullable`
    AND c.`character_set_name` <=> p.`character_set_name`
    AND c.`collation_name` <=> p.`collation_name`
  );

SELECT 'canonical_counts' AS `check_name`,
  (SELECT COUNT(*) FROM `UAT_articles`) AS `articles`,
  (SELECT COUNT(*) FROM `UAT_article_coverage`) AS `coverage`,
  (SELECT COUNT(*) FROM `UAT_article_media`) AS `media`,
  (SELECT COUNT(*) FROM `UAT_article_tags`) AS `tags`,
  (SELECT COUNT(*) FROM `UAT_article_user_groups`) AS `user_groups`;

CHECKSUM TABLE
  `UAT_articles`, `UAT_article_coverage`, `UAT_article_media`,
  `UAT_article_tags`, `UAT_article_user_groups`,
  `UAT_p4_transform_batches`, `UAT_p4_article_identity`, `UAT_p4_articles`,
  `UAT_p4_article_coverage`, `UAT_p4_article_media`, `UAT_p4_article_tags`,
  `UAT_p4_article_user_groups`, `UAT_p4_holds`;
