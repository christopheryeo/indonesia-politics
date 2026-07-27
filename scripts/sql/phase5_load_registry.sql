-- Phase 5 UAT canonical-load registry.
-- Creates one UAT_p5_* audit table only; production is out of scope.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
USE `MSM_dataset_UAT`;

CREATE TABLE `UAT_p5_load_batches` (
  `load_id` char(36) NOT NULL,
  `transform_id` char(36) NOT NULL,
  `load_version` varchar(40) NOT NULL,
  `status` enum('preparing','in_transaction','loaded','validated','rolled_back','failed') NOT NULL,
  `expected_article_count` int unsigned NOT NULL,
  `expected_coverage_count` int unsigned NOT NULL,
  `expected_media_count` int unsigned NOT NULL,
  `expected_tag_count` int unsigned NOT NULL,
  `expected_user_group_count` int unsigned NOT NULL,
  `before_article_count` int unsigned NOT NULL,
  `before_coverage_count` int unsigned NOT NULL,
  `before_media_count` int unsigned NOT NULL,
  `before_tag_count` int unsigned NOT NULL,
  `before_user_group_count` int unsigned NOT NULL,
  `loaded_article_count` int unsigned DEFAULT NULL,
  `loaded_coverage_count` int unsigned DEFAULT NULL,
  `loaded_media_count` int unsigned DEFAULT NULL,
  `loaded_tag_count` int unsigned DEFAULT NULL,
  `loaded_user_group_count` int unsigned DEFAULT NULL,
  `after_article_count` int unsigned DEFAULT NULL,
  `after_coverage_count` int unsigned DEFAULT NULL,
  `after_media_count` int unsigned DEFAULT NULL,
  `after_tag_count` int unsigned DEFAULT NULL,
  `after_user_group_count` int unsigned DEFAULT NULL,
  `started_at` datetime(6) NOT NULL,
  `loaded_at` datetime(6) DEFAULT NULL,
  `validated_at` datetime(6) DEFAULT NULL,
  `notes` text,
  PRIMARY KEY (`load_id`),
  UNIQUE KEY `uq_p5_transform` (`transform_id`),
  KEY `idx_p5_load_status` (`status`),
  CONSTRAINT `fk_p5_load_transform` FOREIGN KEY (`transform_id`)
    REFERENCES `UAT_p4_transform_batches` (`transform_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 5 controlled canonical UAT load registry';
