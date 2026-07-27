-- Phase 3 isolated staging schema for MSM_dataset_UAT.
-- This file creates only UAT_stg_* objects. It does not alter canonical UAT tables.

SET NAMES utf8mb4;
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

CREATE TABLE `UAT_stg_import_batches` (
  `batch_id` char(36) NOT NULL,
  `source_set_hash` char(64) NOT NULL,
  `source_set_name` varchar(200) NOT NULL,
  `mapping_contract_hash` char(64) NOT NULL,
  `loader_version` varchar(40) NOT NULL,
  `status` enum('loading','loaded','validated','failed') NOT NULL,
  `expected_file_count` int unsigned NOT NULL,
  `expected_article_count` int unsigned NOT NULL,
  `expected_coverage_count` int unsigned NOT NULL,
  `expected_media_count` int unsigned NOT NULL,
  `expected_tag_count` int unsigned NOT NULL,
  `expected_user_group_count` int unsigned NOT NULL,
  `expected_precomputed_issue_count` int unsigned NOT NULL,
  `actual_file_count` int unsigned DEFAULT NULL,
  `actual_article_count` int unsigned DEFAULT NULL,
  `actual_coverage_count` int unsigned DEFAULT NULL,
  `actual_media_count` int unsigned DEFAULT NULL,
  `actual_tag_count` int unsigned DEFAULT NULL,
  `actual_user_group_count` int unsigned DEFAULT NULL,
  `actual_issue_count` int unsigned DEFAULT NULL,
  `started_at` datetime(6) NOT NULL,
  `loaded_at` datetime(6) DEFAULT NULL,
  `validated_at` datetime(6) DEFAULT NULL,
  `notes` text,
  PRIMARY KEY (`batch_id`),
  UNIQUE KEY `uq_stg_batch_source_set_hash` (`source_set_hash`),
  KEY `idx_stg_batch_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Phase 3 staging batch registry; one immutable source set per hash';

CREATE TABLE `UAT_stg_source_files` (
  `batch_id` char(36) NOT NULL,
  `source_file_id` int unsigned NOT NULL,
  `source_path` varchar(1000) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `sha256` char(64) NOT NULL,
  `byte_size` bigint unsigned NOT NULL,
  `record_count` int unsigned NOT NULL,
  `first_published_date` datetime DEFAULT NULL,
  `last_published_date` datetime DEFAULT NULL,
  PRIMARY KEY (`batch_id`,`source_file_id`),
  UNIQUE KEY `uq_stg_source_file_hash` (`batch_id`,`sha256`),
  KEY `idx_stg_source_path` (`source_path`(191)),
  CONSTRAINT `fk_stg_file_batch` FOREIGN KEY (`batch_id`)
    REFERENCES `UAT_stg_import_batches` (`batch_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Source-file provenance for each Phase 3 staging batch';

CREATE TABLE `UAT_stg_articles` (
  `batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_file_id` int unsigned NOT NULL,
  `source_row_number` int unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `document_id` int NOT NULL,
  `vendor_article_id` longtext,
  `article_title` longtext,
  `content_title` longtext,
  `content_description` longtext,
  `topic` text,
  `category` text,
  `tone` text,
  `tone_sentiment` text,
  `event_type` text,
  `document_type_id` int DEFAULT NULL,
  `document_type_name` text,
  `product_type` text,
  `article_status` text,
  `group_title` text,
  `news_type` text,
  `published_date` datetime DEFAULT NULL,
  `vendor_indexed_time` datetime DEFAULT NULL,
  `indexed_date_time` datetime DEFAULT NULL,
  `last_updated` datetime DEFAULT NULL,
  `uploaded_by` text,
  `last_updated_by` text,
  `article_hero_image` json NOT NULL,
  `sentiment_list` json NOT NULL,
  `raw_json` json NOT NULL,
  `record_hash` char(64) NOT NULL,
  `validation_status` enum('ready','review','quarantined') NOT NULL,
  PRIMARY KEY (`batch_id`,`staging_article_id`),
  UNIQUE KEY `uq_stg_article_source_id` (`batch_id`,`source_article_id`),
  UNIQUE KEY `uq_stg_article_source_row` (`batch_id`,`source_file_id`,`source_row_number`),
  KEY `idx_stg_article_status` (`batch_id`,`validation_status`),
  KEY `idx_stg_article_published` (`published_date`),
  KEY `idx_stg_article_record_hash` (`record_hash`),
  CONSTRAINT `fk_stg_article_file` FOREIGN KEY (`batch_id`,`source_file_id`)
    REFERENCES `UAT_stg_source_files` (`batch_id`,`source_file_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Immutable normalized article staging plus canonical raw JSON';

CREATE TABLE `UAT_stg_article_coverage` (
  `batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `coverage_type` enum('broadcast','online','print') NOT NULL,
  `coverage_id` int DEFAULT NULL,
  `display_name` text,
  `country` text,
  `media_outlet_category` text,
  `url` text,
  `record_hash` char(64) NOT NULL,
  PRIMARY KEY (`batch_id`,`staging_article_id`,`coverage_type`,`source_ordinal`),
  KEY `idx_stg_coverage_source_article` (`batch_id`,`source_article_id`),
  KEY `idx_stg_coverage_id` (`coverage_id`),
  CONSTRAINT `fk_stg_coverage_article` FOREIGN KEY (`batch_id`,`staging_article_id`)
    REFERENCES `UAT_stg_articles` (`batch_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Flattened broadcast, online and print coverage staging rows';

CREATE TABLE `UAT_stg_article_media` (
  `batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `media_id` int DEFAULT NULL,
  `file_name` text,
  `media_url` text,
  `media_type` text,
  `source` text,
  `record_hash` char(64) NOT NULL,
  PRIMARY KEY (`batch_id`,`staging_article_id`,`source_ordinal`),
  KEY `idx_stg_media_source_article` (`batch_id`,`source_article_id`),
  KEY `idx_stg_media_id` (`media_id`),
  CONSTRAINT `fk_stg_media_article` FOREIGN KEY (`batch_id`,`staging_article_id`)
    REFERENCES `UAT_stg_articles` (`batch_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Flattened media staging rows';

CREATE TABLE `UAT_stg_article_tags` (
  `batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `tag` text NOT NULL,
  `record_hash` char(64) NOT NULL,
  PRIMARY KEY (`batch_id`,`staging_article_id`,`source_ordinal`),
  KEY `idx_stg_tag_source_article` (`batch_id`,`source_article_id`),
  KEY `idx_stg_tag_value` (`tag`(191)),
  CONSTRAINT `fk_stg_tag_article` FOREIGN KEY (`batch_id`,`staging_article_id`)
    REFERENCES `UAT_stg_articles` (`batch_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Source-order-preserving tag staging rows';

CREATE TABLE `UAT_stg_article_user_groups` (
  `batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `source_ordinal` int unsigned NOT NULL,
  `user_group_id` int NOT NULL,
  `record_hash` char(64) NOT NULL,
  PRIMARY KEY (`batch_id`,`staging_article_id`,`source_ordinal`),
  KEY `idx_stg_ug_source_article` (`batch_id`,`source_article_id`),
  KEY `idx_stg_ug_group` (`user_group_id`),
  CONSTRAINT `fk_stg_ug_article` FOREIGN KEY (`batch_id`,`staging_article_id`)
    REFERENCES `UAT_stg_articles` (`batch_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Source-order-preserving user-group staging rows';

CREATE TABLE `UAT_stg_quarantine` (
  `batch_id` char(36) NOT NULL,
  `staging_article_id` bigint unsigned NOT NULL,
  `source_article_id` int NOT NULL,
  `rule_code` varchar(64) NOT NULL,
  `severity` enum('warning','error') NOT NULL,
  `field_name` varchar(100) NOT NULL,
  `observed_value` longtext,
  `details` text NOT NULL,
  `review_status` enum('pending','approved','rejected','resolved') NOT NULL DEFAULT 'pending',
  `reviewed_at` datetime DEFAULT NULL,
  `reviewed_by` varchar(100) DEFAULT NULL,
  `resolution_notes` text,
  PRIMARY KEY (`batch_id`,`staging_article_id`,`rule_code`,`field_name`),
  KEY `idx_stg_quarantine_rule` (`batch_id`,`rule_code`,`severity`),
  KEY `idx_stg_quarantine_review` (`batch_id`,`review_status`),
  CONSTRAINT `fk_stg_quarantine_article` FOREIGN KEY (`batch_id`,`staging_article_id`)
    REFERENCES `UAT_stg_articles` (`batch_id`,`staging_article_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Explicit Phase 3 error and warning review queue';
