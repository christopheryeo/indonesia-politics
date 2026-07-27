-- EMERGENCY UAT-ONLY rollback for Phase 5 load a44faa80-c422-4078-a302-f3676fe2434b.
-- Do not run during normal processing. Deleting the loaded parent IDs cascades
-- only to their four canonical UAT child tables. Production is never referenced.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
USE `MSM_dataset_UAT`;

SET @load_id = 'a44faa80-c422-4078-a302-f3676fe2434b';
SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';

START TRANSACTION;

DELETE a
FROM `UAT_articles` a
JOIN `UAT_p4_articles` p ON p.`article_id` = a.`article_id`
WHERE p.`transform_id` = @transform_id
  AND EXISTS (
    SELECT 1
    FROM `UAT_p5_load_batches` b
    WHERE b.`load_id` = @load_id
      AND b.`transform_id` = @transform_id
      AND b.`status` = 'validated'
  );

SET @deleted_articles = ROW_COUNT();

SELECT
  @deleted_articles AS `deleted_articles`,
  (SELECT COUNT(*) FROM `UAT_articles`) AS `remaining_articles`,
  (SELECT COUNT(*) FROM `UAT_article_coverage`) AS `remaining_coverage`,
  (SELECT COUNT(*) FROM `UAT_article_media`) AS `remaining_media`,
  (SELECT COUNT(*) FROM `UAT_article_tags`) AS `remaining_tags`,
  (SELECT COUNT(*) FROM `UAT_article_user_groups`) AS `remaining_user_groups`;

-- Expected rollback gate before committing:
-- deleted_articles=8140; remaining counts=13789,27355,420,224501,9287.
-- Update the registry and COMMIT only after those values are confirmed.
-- Otherwise issue ROLLBACK.
