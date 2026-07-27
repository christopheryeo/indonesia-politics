-- Load validated Phase 4 candidates into canonical UAT inside one transaction.
-- IMPORTANT: this file intentionally does not COMMIT. Run phase5_validate_uncommitted.sql
-- in the same session, inspect every gate, and only then issue the final status
-- update and COMMIT.

SET NAMES utf8mb4;
SET SESSION collation_connection = 'utf8mb4_unicode_ci';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
USE `MSM_dataset_UAT`;

SET @load_id = 'a44faa80-c422-4078-a302-f3676fe2434b';
SET @transform_id = 'f53cc692-85b8-11f1-ba76-42010a512009';

START TRANSACTION;

UPDATE `UAT_p5_load_batches`
SET `status` = 'in_transaction'
WHERE `load_id` = @load_id
  AND `transform_id` = @transform_id
  AND `status` = 'preparing';

INSERT INTO `UAT_articles` (
  `article_id`, `document_id`, `vendor_article_id`, `article_title`, `content_title`,
  `content_description`, `topic`, `category`, `tone`, `tone_sentiment`, `event_type`,
  `document_type_id`, `document_type_name`, `product_type`, `article_status`,
  `group_title`, `news_type`, `published_date`, `vendor_indexed_time`,
  `indexed_date_time`, `last_updated`, `uploaded_by`, `last_updated_by`
)
SELECT
  p.`article_id`, p.`document_id`, p.`vendor_article_id`, p.`article_title`, p.`content_title`,
  p.`content_description`, p.`topic`, p.`category`, p.`tone`, p.`tone_sentiment`, p.`event_type`,
  p.`document_type_id`, p.`document_type_name`, p.`product_type`, p.`article_status`,
  p.`group_title`, p.`news_type`, p.`published_date`, p.`vendor_indexed_time`,
  p.`indexed_date_time`, p.`last_updated`, p.`uploaded_by`, p.`last_updated_by`
FROM `UAT_p4_articles` p
JOIN `UAT_p4_transform_batches` t ON t.`transform_id` = p.`transform_id`
WHERE p.`transform_id` = @transform_id
  AND t.`status` = 'validated'
ORDER BY p.`article_id`;

SET @inserted_articles = ROW_COUNT();

INSERT INTO `UAT_article_coverage` (
  `article_id`, `coverage_id`, `coverage_type`, `display_name`,
  `country`, `media_outlet_category`, `url`
)
SELECT
  c.`article_id`, c.`coverage_id`, c.`coverage_type`, c.`display_name`,
  c.`country`, c.`media_outlet_category`, c.`url`
FROM `UAT_p4_article_coverage` c
WHERE c.`transform_id` = @transform_id
ORDER BY c.`article_id`, c.`coverage_type`, c.`source_ordinal`;

SET @inserted_coverage = ROW_COUNT();

INSERT INTO `UAT_article_media` (
  `article_id`, `media_id`, `file_name`, `media_url`, `media_type`, `source`
)
SELECT
  m.`article_id`, m.`media_id`, m.`file_name`, m.`media_url`, m.`media_type`, m.`source`
FROM `UAT_p4_article_media` m
WHERE m.`transform_id` = @transform_id
ORDER BY m.`article_id`, m.`source_ordinal`;

SET @inserted_media = ROW_COUNT();

INSERT INTO `UAT_article_tags` (`article_id`, `tag`)
SELECT t.`article_id`, t.`tag`
FROM `UAT_p4_article_tags` t
WHERE t.`transform_id` = @transform_id
ORDER BY t.`article_id`, t.`source_ordinal`;

SET @inserted_tags = ROW_COUNT();

INSERT INTO `UAT_article_user_groups` (`article_id`, `user_group_id`)
SELECT u.`article_id`, u.`user_group_id`
FROM `UAT_p4_article_user_groups` u
WHERE u.`transform_id` = @transform_id
ORDER BY u.`article_id`, u.`source_ordinal`;

SET @inserted_user_groups = ROW_COUNT();

UPDATE `UAT_p5_load_batches`
SET
  `status` = 'loaded',
  `loaded_article_count` = @inserted_articles,
  `loaded_coverage_count` = @inserted_coverage,
  `loaded_media_count` = @inserted_media,
  `loaded_tag_count` = @inserted_tags,
  `loaded_user_group_count` = @inserted_user_groups,
  `after_article_count` = (SELECT COUNT(*) FROM `UAT_articles`),
  `after_coverage_count` = (SELECT COUNT(*) FROM `UAT_article_coverage`),
  `after_media_count` = (SELECT COUNT(*) FROM `UAT_article_media`),
  `after_tag_count` = (SELECT COUNT(*) FROM `UAT_article_tags`),
  `after_user_group_count` = (SELECT COUNT(*) FROM `UAT_article_user_groups`),
  `loaded_at` = UTC_TIMESTAMP(6)
WHERE `load_id` = @load_id;

SELECT
  @inserted_articles AS `inserted_articles`,
  @inserted_coverage AS `inserted_coverage`,
  @inserted_media AS `inserted_media`,
  @inserted_tags AS `inserted_tags`,
  @inserted_user_groups AS `inserted_user_groups`;

SELECT `status`, `before_article_count`, `after_article_count`,
       `before_coverage_count`, `after_coverage_count`,
       `before_media_count`, `after_media_count`,
       `before_tag_count`, `after_tag_count`,
       `before_user_group_count`, `after_user_group_count`
FROM `UAT_p5_load_batches`
WHERE `load_id` = @load_id;
