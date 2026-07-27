# Migration Plan: `media-monitoring` to `indonesia-politics`

## Source Baseline

- Source: `Alex (Dev)/media-monitoring`
- Destination: `Alex (Dev)/indonesia-politics`
- Source branch: `main`
- Source commit: `d969639` (`Improve query latency tooling`)
- Verified state: the source working tree is clean and `main` matches `origin/main`

Only files committed at `d969639` will be used as the migration baseline. The source project will remain unchanged.

## Objectives

1. Create a runnable Indonesia-politics monitoring system in `Alex (Dev)/indonesia-politics`.
2. Retain only reusable system folders and system files from `media-monitoring`.
3. Exclude all corpus data, operational history, credentials, generated artifacts, local state, and source Git history.
4. Preserve the query-optimisation implementation and tests committed in `d969639`.
5. Adapt the retained system from SAF/MINDEF monitoring to Indonesian political-media monitoring.
6. Ensure the migrated system operates correctly with an empty corpus.
7. Initialise `indonesia-politics` with fresh standalone Git history.

## Migration Procedure

### 1. Lock and verify the source

1. Confirm `media-monitoring` is on branch `main` at commit `d969639`.
2. Confirm its working tree is clean and `main` matches `origin/main`.
3. Record the source commit, Git status, and filesystem checksums before migration.
4. Abort the migration if the source state has changed until the new state is reviewed.
5. Copy only content committed at `d969639`; do not copy arbitrary working-tree files.

### 2. Retain the runnable system

Retain and adapt:

1. Python programs, SQL definitions, and operating procedures under `scripts/`.
2. Automated tests under `tests/`, including `tests/test_query.py`.
3. Frozen entity schemas under `schemas/`.
4. Dashboard application source, tests, package manifests, and generic dashboard definitions.
5. Stable Obsidian configuration that is not specific to a local workspace.
6. `.gitignore`, `README.md`, `AGENTS.md`, and `wiki.yaml`.
7. The following entity-domain folders:
   - `entities/article`
   - `entities/appointments`
   - `entities/country`
   - `entities/decisions`
   - `entities/issues`
   - `entities/organisations`
   - `entities/outlet`
   - `entities/people`
   - `entities/place`
   - `entities/search`
   - `entities/topic`
8. Empty runtime structures:
   - `Inputs/articles`
   - `raw`
   - `runs`
   - `index`
   - `tmp`
   - `topics`

Use `.gitkeep` placeholders where necessary to preserve intentional empty directories.

### 3. Exclude all data and local state

Do not migrate:

1. Files under `Inputs/articles/`.
2. Raw feeds, source exports, archives, and validation datasets under `raw/`.
3. Compiled articles under `entities/article/`.
4. Entity notes for people, organisations, countries, places, outlets, appointments, topics, searches, issues, or decisions.
5. Existing issue assessments and source-corpus decision records.
6. Generated catalog contents.
7. Historical entity log entries.
8. SQLite databases and generated indexes, including `index/wiki.db`.
9. Run receipts, staging bundles, previews, and diagnostic artifacts.
10. Monitoring-topic definitions and state, including `topics/sa26.json`.
11. Corpus-specific test fixtures, including golden answers derived from the SAF/MINDEF corpus.
12. Dashboard chat history, generated dashboard data, deployment state, and hosting identity.
13. `.env.local`, API keys, passwords, tokens, database credentials, and connection files.
14. `.DS_Store`, `__pycache__`, `.pytest_cache`, `node_modules`, build output, caches, and temporary files.
15. Local editor and agent state such as `.claude/settings.local.json` and `.obsidian/workspace.json`.
16. The source `.git` directory, rewrite metadata, worktrees, branches, commits, remotes, and Git objects.

### 4. Reset entity system files

For every entity domain:

1. Retain and adapt `index.md` as the operating manual and schema registry.
2. Recreate `catalog.md` with its valid structure and column headers but no entity rows.
3. Recreate `log.md` with an empty-ledger header and no historical entries.
4. Remove source-corpus examples, article identifiers, entity names, and wikilinks.
5. Preserve the domain's operating rules, schema requirements, generation rules, and audit behaviour.

### 5. Adapt the system for Indonesia politics

1. Set the vault name to `indonesia-politics`.
2. Describe its purpose as Indonesian political-media monitoring.
3. Replace SAF/MINDEF/DSTA names, branding, assumptions, examples, and defaults in system documentation, configuration, code, dashboard text, and tests.
4. Generalise SAF-specific sensitive-content flags and query controls into neutral sensitive-content terminology.
5. Start with no active monitoring topics, sources, schedules, or previous-run state.
6. Preserve Singapore time as the operator timezone where required, not as corpus configuration.
7. Add a secrets-free `.env.example` containing variable names and setup guidance only.
8. Ensure all filesystem references are destination-relative and do not point to `media-monitoring`.
9. Update `.gitignore` so future corpus data, databases, run receipts, credentials, dependencies, caches, and generated artifacts remain untracked.

### 6. Support an empty vault

1. Replace corpus-dependent tests with small synthetic fixtures created in temporary test directories.
2. Ensure catalog generation succeeds with zero entity records.
3. Ensure link checking succeeds with zero corpus links.
4. Ensure ingestion dry runs succeed with zero input articles.
5. Ensure queries return a clear `no matching data` result rather than failing.
6. Ensure dashboard-data generation produces valid zero-state metrics.
7. Ensure the dashboard renders an intentional empty state.
8. Preserve and run the query-optimisation tests committed in `d969639`.

### 7. Establish fresh version control

1. Initialise a new standalone Git repository inside `indonesia-politics`.
2. Do not copy source Git objects, refs, worktrees, remotes, or commit history.
3. Record `media-monitoring@d969639` as provenance in project documentation without importing its history.
4. Stage only files permitted by the approved system allowlist.
5. Create the initial commit only after all migration tests pass.

## Tests

### Source baseline and integrity

1. Confirm the source branch is `main`.
2. Confirm source `HEAD` is `d969639`.
3. Confirm source `main` matches `origin/main`.
4. Confirm the source working tree is clean before and after migration.
5. Compare pre- and post-migration source checksums to prove the source was not modified.

### Data-isolation tests

1. Verify that `Inputs/articles` contains zero article files.
2. Verify that `entities/article` contains zero compiled articles.
3. Verify that no entity notes exist beyond approved system files and placeholders.
4. Verify that every `catalog.md` contains zero entity rows.
5. Verify that every `log.md` contains zero historical entries.
6. Verify that `raw`, `runs`, `index`, `tmp`, and `topics` contain no migrated operational data.
7. Search for source article IDs, run timestamps, source filenames, and known corpus-specific entities.
8. Scan for credentials, tokens, passwords, connection strings, `.env.local`, databases, and archives.
9. Verify that no source Git object, ref, remote, worktree, or rewrite file exists in the destination.
10. Repeat the isolation scan against both the destination working tree and its committed Git objects.

### Structural tests

1. Compare the destination inventory against an explicit system-file allowlist.
2. Confirm every required system and runtime directory exists.
3. Confirm every entity domain contains `index.md`, `catalog.md`, and `log.md`.
4. Validate all YAML and JSON files.
5. Confirm all retained scripts use destination-relative paths.
6. Confirm no retained file references the source `media-monitoring` path.
7. Confirm `.gitignore` excludes every data, secret, database, receipt, dependency, cache, and generated-output category.

### Functional tests

1. Run the complete Python test suite.
2. Run the committed query-optimisation tests.
3. Generate catalogs against the empty vault and verify valid zero-row output.
4. Run the read-only link checker and verify a clean empty-vault result.
5. Run an empty-input ingestion dry run.
6. Run an empty-corpus query and verify graceful `no matching data` output.
7. Generate dashboard data and verify valid zero-state metrics.
8. Install dashboard dependencies from the lockfile.
9. Run dashboard linting, automated tests, and the production build.
10. Verify that the dashboard renders the Indonesia-politics identity and empty state.

### Destination Git tests

1. Confirm the destination repository has fresh history.
2. Confirm no source remote is configured.
3. Confirm the initial commit contains only approved system files.
4. Confirm ignored data paths remain untracked when populated with temporary test files.
5. Confirm the destination working tree is clean after the initial commit.

## End Conditions

The migration is complete only when:

1. `media-monitoring` remains clean, unchanged, and at commit `d969639`.
2. `indonesia-politics` contains a runnable, Indonesia-adapted monitoring system.
3. No source corpus, raw feed, entity record, issue assessment, run history, database, monitoring-topic state, credential, generated artifact, or source Git history is present.
4. The query-optimisation implementation and tests from `d969639` are included.
5. Every entity domain contains an adapted `index.md`, an empty `catalog.md`, and an empty `log.md`.
6. The system handles an empty corpus without errors.
7. All source-integrity, data-isolation, structural, functional, dashboard, and Git tests pass.
8. The destination's initial commit contains only approved system folders and system files.
