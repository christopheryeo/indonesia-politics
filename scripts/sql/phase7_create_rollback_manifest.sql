-- Create the Phase 5 loaded-ID rollback manifest in the isolated Phase 7 schema.
-- Reads provenance from live UAT but writes only to the rehearsal schema.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
USE `MSM_dataset_UAT_PHASE7_REHEARSAL_20260723`;

CREATE TABLE `phase7_loaded_article_ids` (
  `article_id` int NOT NULL,
  `source_article_id` int NOT NULL,
  `source_record_hash` char(64) NOT NULL,
  `transform_id` char(36) NOT NULL,
  PRIMARY KEY (`article_id`),
  UNIQUE KEY `uq_phase7_source_article_id` (`source_article_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Isolated Phase 7 rollback manifest; not part of canonical UAT';

INSERT INTO `phase7_loaded_article_ids` (
  `article_id`, `source_article_id`, `source_record_hash`, `transform_id`
)
SELECT p.`article_id`, p.`source_article_id`, p.`source_record_hash`, p.`transform_id`
FROM `MSM_dataset_UAT`.`UAT_p4_articles` p
WHERE p.`transform_id` = 'f53cc692-85b8-11f1-ba76-42010a512009';

SELECT
  COUNT(*) AS `manifest_rows`,
  COUNT(DISTINCT `article_id`) AS `distinct_target_ids`,
  COUNT(DISTINCT `source_article_id`) AS `distinct_source_ids`,
  MIN(`article_id`) AS `min_target_id`,
  MAX(`article_id`) AS `max_target_id`
FROM `phase7_loaded_article_ids`;

SELECT COUNT(*) AS `manifest_ids_missing_from_rehearsal`
FROM `phase7_loaded_article_ids` m
LEFT JOIN `UAT_articles` a ON a.`article_id` = m.`article_id`
WHERE a.`article_id` IS NULL;
