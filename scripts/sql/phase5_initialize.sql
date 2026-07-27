-- Initialise the audited Phase 5 load after the read-only preflight passes.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
USE `MSM_dataset_UAT`;

INSERT INTO `UAT_p5_load_batches` (
  `load_id`, `transform_id`, `load_version`, `status`,
  `expected_article_count`, `expected_coverage_count`, `expected_media_count`,
  `expected_tag_count`, `expected_user_group_count`,
  `before_article_count`, `before_coverage_count`, `before_media_count`,
  `before_tag_count`, `before_user_group_count`, `started_at`, `notes`
)
SELECT
  'a44faa80-c422-4078-a302-f3676fe2434b',
  t.`transform_id`,
  'phase5-canonical-uat-load.v1',
  'preparing',
  t.`candidate_article_count`, t.`candidate_coverage_count`, t.`candidate_media_count`,
  t.`candidate_tag_count`, t.`candidate_user_group_count`,
  (SELECT COUNT(*) FROM `UAT_articles`),
  (SELECT COUNT(*) FROM `UAT_article_coverage`),
  (SELECT COUNT(*) FROM `UAT_article_media`),
  (SELECT COUNT(*) FROM `UAT_article_tags`),
  (SELECT COUNT(*) FROM `UAT_article_user_groups`),
  UTC_TIMESTAMP(6),
  'Phase 5 canonical UAT load; 66 review and 9 quarantined articles excluded; production excluded'
FROM `UAT_p4_transform_batches` t
WHERE t.`transform_id` = 'f53cc692-85b8-11f1-ba76-42010a512009'
  AND t.`status` = 'validated'
  AND NOT EXISTS (
    SELECT 1
    FROM `UAT_p4_articles` p
    JOIN `UAT_articles` a ON a.`article_id` = p.`article_id`
    WHERE p.`transform_id` = t.`transform_id`
  );

SELECT *
FROM `UAT_p5_load_batches`
WHERE `load_id` = 'a44faa80-c422-4078-a302-f3676fe2434b';
