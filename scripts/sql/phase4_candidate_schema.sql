-- Phase 4 canonical-shaped candidate schema for MSM_dataset_UAT.
-- Creates UAT_p4_* objects only. It never alters the five canonical UAT tables.

SET NAMES utf8mb4;
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
USE `MSM_dataset_UAT`;

CREATE TABLE `UAT_p4_transform_batches` (
  `transform_id` char(36) NOT NULL,
  `source_batch_id` char(36) NOT NULL,
  `transform_version` varchar(40) NOT NULL,
  `status` enum('building','built','validated','failed') NOT NULL,
  `allocation_ceiling` int NOT NULL,
  `source_article_count` int unsigned NOT NULL,
  `candidate_article_count` int unsigned DEFAULT NULL,
  `review_article_count` int unsigned DEFAULT NULL,
  `quarantined_article_count` int unsigned DEFAULT NULL,
  `candidate_coverage_count` int unsigned DEFAULT NULL,
  `candidate_media_count` int unsigned DEFAULT NULL,
  `candidate_tag_count` int unsigned DEFAULT NULL,
  `candidate_user_group_count` int unsigned DEFAULT NULL,
  `started_at` datetime(6) NOT NULL,
  `built_at` datetime(6) DEFAULT NULL,
  `validated_at` datetime(6) DEFAULT NULL,
  `notes` text,
  PRIMARY KEY (`transform_id`),
  UNIQUE KEY `uq_p4_source_batch` (`source_batch_id`),
  KEY `idx_p4_transform_status` (`status`),
  CONSTRAINT `fk_p4_transform_source_batch` FOREIGN KEY (`source_batch_id`)
    REFERENCES `UAT_stg_import_batches` (`batch_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 4 UAT-only transformation registry';

CREATE TABLE `UAT_p4_article_identity` (
  `transform_id` char(36) NOT NULL,
  `source_batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `target_article_id` int NOT NULL,
  `identity_action` enum('preserved','remapped_collision') NOT NULL,
  `disposition` enum('candidate','review','quarantined') NOT NULL,
  `blocking_issue_count` int unsigned NOT NULL,
  `warning_issue_count` int unsigned NOT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`staging_article_id`),
  UNIQUE KEY `uq_p4_identity_source_id` (`transform_id`,`source_article_id`),
  UNIQUE KEY `uq_p4_identity_target_id` (`transform_id`,`target_article_id`),
  KEY `idx_p4_identity_disposition` (`transform_id`,`disposition`),
  KEY `idx_p4_identity_source_article` (`source_batch_id`,`staging_article_id`),
  CONSTRAINT `fk_p4_identity_transform` FOREIGN KEY (`transform_id`)
    REFERENCES `UAT_p4_transform_batches` (`transform_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_p4_identity_staging_article` FOREIGN KEY (`source_batch_id`,`staging_article_id`)
    REFERENCES `UAT_stg_articles` (`batch_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Explicit external-source to candidate UAT article ID crosswalk';

CREATE TABLE `UAT_p4_articles` (
  `transform_id` char(36) NOT NULL,
  `source_batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `article_id` int NOT NULL,
  `document_id` int NOT NULL,
  `vendor_article_id` varchar(400) DEFAULT NULL,
  `article_title` varchar(500) DEFAULT NULL,
  `content_title` varchar(500) DEFAULT NULL,
  `content_description` longtext,
  `topic` varchar(200) DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `tone` varchar(20) DEFAULT NULL,
  `tone_sentiment` varchar(20) DEFAULT NULL,
  `event_type` varchar(20) DEFAULT NULL,
  `document_type_id` tinyint unsigned DEFAULT NULL,
  `document_type_name` varchar(50) DEFAULT NULL,
  `product_type` varchar(20) DEFAULT NULL,
  `article_status` char(1) DEFAULT NULL,
  `group_title` varchar(300) DEFAULT NULL,
  `news_type` varchar(100) DEFAULT NULL,
  `published_date` datetime DEFAULT NULL,
  `vendor_indexed_time` datetime DEFAULT NULL,
  `indexed_date_time` datetime DEFAULT NULL,
  `last_updated` datetime DEFAULT NULL,
  `uploaded_by` varchar(50) DEFAULT NULL,
  `last_updated_by` varchar(50) DEFAULT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`article_id`),
  UNIQUE KEY `uq_p4_article_staging` (`transform_id`,`staging_article_id`),
  UNIQUE KEY `uq_p4_article_source_id` (`transform_id`,`source_article_id`),
  KEY `idx_p4_article_published` (`published_date`),
  CONSTRAINT `fk_p4_article_identity` FOREIGN KEY (`transform_id`,`staging_article_id`)
    REFERENCES `UAT_p4_article_identity` (`transform_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Canonical-shaped Phase 4 candidate articles; not the UAT canonical table';

CREATE TABLE `UAT_p4_article_coverage` (
  `transform_id` char(36) NOT NULL,
  `article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `coverage_id` int DEFAULT NULL,
  `coverage_type` enum('broadcast','online','print') NOT NULL,
  `display_name` varchar(200) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `media_outlet_category` varchar(100) DEFAULT NULL,
  `url` varchar(1000) DEFAULT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`article_id`,`coverage_type`,`source_ordinal`),
  KEY `idx_p4_coverage_article` (`transform_id`,`article_id`),
  CONSTRAINT `fk_p4_coverage_article` FOREIGN KEY (`transform_id`,`article_id`)
    REFERENCES `UAT_p4_articles` (`transform_id`,`article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Canonical-shaped Phase 4 candidate coverage rows';

CREATE TABLE `UAT_p4_article_media` (
  `transform_id` char(36) NOT NULL,
  `article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `media_id` int DEFAULT NULL,
  `file_name` varchar(500) DEFAULT NULL,
  `media_url` varchar(1000) DEFAULT NULL,
  `media_type` varchar(30) DEFAULT NULL,
  `source` varchar(200) DEFAULT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`article_id`,`source_ordinal`),
  KEY `idx_p4_media_article` (`transform_id`,`article_id`),
  CONSTRAINT `fk_p4_media_article` FOREIGN KEY (`transform_id`,`article_id`)
    REFERENCES `UAT_p4_articles` (`transform_id`,`article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Canonical-shaped Phase 4 candidate media rows';

CREATE TABLE `UAT_p4_article_tags` (
  `transform_id` char(36) NOT NULL,
  `article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `tag` varchar(200) NOT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`article_id`,`source_ordinal`),
  KEY `idx_p4_tag_article` (`transform_id`,`article_id`),
  KEY `idx_p4_tag_value` (`tag`),
  CONSTRAINT `fk_p4_tag_article` FOREIGN KEY (`transform_id`,`article_id`)
    REFERENCES `UAT_p4_articles` (`transform_id`,`article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Canonical-shaped Phase 4 candidate tags';

CREATE TABLE `UAT_p4_article_user_groups` (
  `transform_id` char(36) NOT NULL,
  `article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `user_group_id` int NOT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`article_id`,`source_ordinal`),
  KEY `idx_p4_user_group_article` (`transform_id`,`article_id`),
  KEY `idx_p4_user_group_id` (`user_group_id`),
  CONSTRAINT `fk_p4_user_group_article` FOREIGN KEY (`transform_id`,`article_id`)
    REFERENCES `UAT_p4_articles` (`transform_id`,`article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Canonical-shaped Phase 4 candidate user groups';

CREATE TABLE `UAT_p4_holds` (
  `transform_id` char(36) NOT NULL,
  `source_batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `target_article_id` int NOT NULL,
  `disposition` enum('review','quarantined') NOT NULL,
  `blocking_issue_count` int unsigned NOT NULL,
  `warning_issue_count` int unsigned NOT NULL,
  `rule_codes` text NOT NULL,
  `source_record_hash` char(64) NOT NULL,
  PRIMARY KEY (`transform_id`,`staging_article_id`),
  KEY `idx_p4_hold_disposition` (`transform_id`,`disposition`),
  CONSTRAINT `fk_p4_hold_identity` FOREIGN KEY (`transform_id`,`staging_article_id`)
    REFERENCES `UAT_p4_article_identity` (`transform_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 4 records held from candidate loading pending review or correction';
