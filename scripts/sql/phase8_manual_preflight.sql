-- Phase 8 MANUAL production preflight (read-only).
-- This script performs SELECTs only. It does not start a write transaction.
-- Target: MSM_dataset. Validated source: MSM_dataset_UAT Phase 4 candidates.
-- Every result named failure_count must be zero before a manual cutover.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION TRANSACTION READ ONLY;
SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';
SET @load_id = 'a44faa80-c422-4078-a302-f3676fe2434b';

START TRANSACTION WITH CONSISTENT SNAPSHOT;

SELECT 'target_identity' AS `check_name`, DATABASE() AS `connection_default_database`,
       'MSM_dataset' AS `intended_target`, UTC_TIMESTAMP(6) AS `checked_at_utc`;

SELECT 'required_target_objects_missing' AS `check_name`, 7 - COUNT(*) AS `failure_count`
FROM information_schema.tables
WHERE table_schema = 'MSM_dataset'
  AND table_name IN (
    'articles', 'article_coverage', 'article_media', 'article_tags',
    'article_user_groups', 'v_article_coverage_summary', 'v_outlet_daily_volume'
  );

SELECT 'source_phase_gates' AS `check_name`,
  (SELECT COUNT(*) <> 1 FROM `MSM_dataset_UAT`.`UAT_p4_transform_batches`
    WHERE `transform_id` = @transform_id AND `status` = 'validated')
  +
  (SELECT COUNT(*) <> 1 FROM `MSM_dataset_UAT`.`UAT_p5_load_batches`
    WHERE `load_id` = @load_id AND `transform_id` = @transform_id
      AND `status` = 'validated' AND `loaded_article_count` = 8140)
  AS `failure_count`;

SELECT 'source_candidate_count_mismatch' AS `check_name`,
  ((SELECT COUNT(*) FROM `MSM_dataset_UAT`.`UAT_p4_articles` WHERE `transform_id` = @transform_id) <> 8140)
  + ((SELECT COUNT(*) FROM `MSM_dataset_UAT`.`UAT_p4_article_coverage` WHERE `transform_id` = @transform_id) <> 8140)
  + ((SELECT COUNT(*) FROM `MSM_dataset_UAT`.`UAT_p4_article_media` WHERE `transform_id` = @transform_id) <> 343)
  + ((SELECT COUNT(*) FROM `MSM_dataset_UAT`.`UAT_p4_article_tags` WHERE `transform_id` = @transform_id) <> 227222)
  + ((SELECT COUNT(*) FROM `MSM_dataset_UAT`.`UAT_p4_article_user_groups` WHERE `transform_id` = @transform_id) <> 8140)
  + ((SELECT COUNT(*) FROM `MSM_dataset_UAT`.`UAT_p4_holds` WHERE `transform_id` = @transform_id) <> 75)
  AS `failure_count`;

WITH expected AS (
  SELECT REPLACE(`table_name`, 'UAT_', '') AS `table_name`, `ordinal_position`, `column_name`,
         `column_type`, `is_nullable`, COALESCE(`character_set_name`, '') AS `character_set_name`,
         COALESCE(`collation_name`, '') AS `collation_name`, `extra`
  FROM information_schema.columns
  WHERE `table_schema` = 'MSM_dataset_UAT'
    AND `table_name` IN ('UAT_articles','UAT_article_coverage','UAT_article_media','UAT_article_tags','UAT_article_user_groups')
), actual AS (
  SELECT `table_name`, `ordinal_position`, `column_name`, `column_type`, `is_nullable`,
         COALESCE(`character_set_name`, '') AS `character_set_name`,
         COALESCE(`collation_name`, '') AS `collation_name`, `extra`
  FROM information_schema.columns
  WHERE `table_schema` = 'MSM_dataset'
    AND `table_name` IN ('articles','article_coverage','article_media','article_tags','article_user_groups')
), differences AS (
  SELECT e.`table_name`, e.`column_name`
  FROM expected e
  LEFT JOIN actual a
    ON a.`table_name` = e.`table_name` AND a.`ordinal_position` = e.`ordinal_position`
   AND a.`column_name` = e.`column_name` AND a.`column_type` = e.`column_type`
   AND a.`is_nullable` = e.`is_nullable` AND a.`character_set_name` = e.`character_set_name`
   AND a.`collation_name` = e.`collation_name` AND a.`extra` = e.`extra`
  WHERE a.`column_name` IS NULL
  UNION ALL
  SELECT a.`table_name`, a.`column_name`
  FROM actual a
  LEFT JOIN expected e
    ON e.`table_name` = a.`table_name` AND e.`ordinal_position` = a.`ordinal_position`
   AND e.`column_name` = a.`column_name` AND e.`column_type` = a.`column_type`
   AND e.`is_nullable` = a.`is_nullable` AND e.`character_set_name` = a.`character_set_name`
   AND e.`collation_name` = a.`collation_name` AND e.`extra` = a.`extra`
  WHERE e.`column_name` IS NULL
)
SELECT 'target_column_definition_mismatch' AS `check_name`, COUNT(*) AS `failure_count`
FROM differences;

SELECT 'target_foreign_key_gate' AS `check_name`,
       4 - COUNT(*) AS `failure_count`
FROM information_schema.referential_constraints
WHERE `constraint_schema` = 'MSM_dataset'
  AND `table_name` IN ('article_coverage','article_media','article_tags','article_user_groups')
  AND `referenced_table_name` = 'articles'
  AND `delete_rule` = 'CASCADE' AND `update_rule` = 'CASCADE';

SELECT 'candidate_article_id_collision' AS `check_name`, COUNT(*) AS `failure_count`
FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
JOIN `MSM_dataset`.`articles` a ON a.`article_id` = p.`article_id`
WHERE p.`transform_id` = @transform_id;

SELECT 'candidate_vendor_id_collision' AS `check_name`,
       COUNT(DISTINCT p.`article_id`) AS `failure_count`
FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
JOIN `MSM_dataset`.`articles` a ON a.`vendor_article_id` = p.`vendor_article_id`
WHERE p.`transform_id` = @transform_id AND p.`vendor_article_id` IS NOT NULL;

SELECT 'candidate_exact_story_collision' AS `check_name`,
       COUNT(DISTINCT p.`article_id`) AS `failure_count`
FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
JOIN `MSM_dataset`.`articles` a
  ON a.`vendor_article_id` <=> p.`vendor_article_id`
 AND a.`article_title` <=> p.`article_title`
 AND a.`published_date` <=> p.`published_date`
WHERE p.`transform_id` = @transform_id;

SELECT 'target_global_orphans' AS `check_name`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage` c LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id` = c.`article_id` WHERE a.`article_id` IS NULL)
  + (SELECT COUNT(*) FROM `MSM_dataset`.`article_media` m LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id` = m.`article_id` WHERE a.`article_id` IS NULL)
  + (SELECT COUNT(*) FROM `MSM_dataset`.`article_tags` t LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id` = t.`article_id` WHERE a.`article_id` IS NULL)
  + (SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups` u LEFT JOIN `MSM_dataset`.`articles` a ON a.`article_id` = u.`article_id` WHERE a.`article_id` IS NULL)
  AS `failure_count`;

SELECT 'target_baseline' AS `check_name`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`articles`) AS `articles`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_coverage`) AS `coverage`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_media`) AS `media`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_tags`) AS `tags`,
  (SELECT COUNT(*) FROM `MSM_dataset`.`article_user_groups`) AS `user_groups`,
  (SELECT MIN(`article_id`) FROM `MSM_dataset_UAT`.`UAT_p4_articles` WHERE `transform_id` = @transform_id) AS `candidate_min_id`,
  (SELECT MAX(`article_id`) FROM `MSM_dataset_UAT`.`UAT_p4_articles` WHERE `transform_id` = @transform_id) AS `candidate_max_id`;

COMMIT;
