-- Rehearse the Phase 5 rollback inside the isolated Phase 7 schema.
-- IMPORTANT: this file intentionally does not COMMIT.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
USE `MSM_dataset_UAT_PHASE7_REHEARSAL_20260723`;

START TRANSACTION;

DELETE a
FROM `UAT_articles` a
JOIN `phase7_loaded_article_ids` m ON m.`article_id` = a.`article_id`;

SET @phase7_deleted_articles = ROW_COUNT();

SELECT
  @phase7_deleted_articles AS `deleted_articles`,
  (SELECT COUNT(*) FROM `UAT_articles`) AS `remaining_articles`,
  (SELECT COUNT(*) FROM `UAT_article_coverage`) AS `remaining_coverage`,
  (SELECT COUNT(*) FROM `UAT_article_media`) AS `remaining_media`,
  (SELECT COUNT(*) FROM `UAT_article_tags`) AS `remaining_tags`,
  (SELECT COUNT(*) FROM `UAT_article_user_groups`) AS `remaining_user_groups`;
