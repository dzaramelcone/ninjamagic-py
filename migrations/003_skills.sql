/*
SCRIPT:
pg-schema-diff plan --from-dsn "postgres://postgres:postgres@localhost:5432/postgres" --to-dir ./ninjamagic/sqlc/schema.sql > ./migrations/003_skills.sql
cat ./migrations/003_skills.sql | docker exec -i db psql -U postgres
Statement 0
  - Backfill skills from legacy character columns
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
INSERT INTO "public"."skills" (char_id, name, rank, tnl)
SELECT id, 'Martial Arts', rank_martial_arts, tnl_martial_arts FROM "public"."characters"
ON CONFLICT (char_id, name) DO UPDATE
SET rank = EXCLUDED.rank,
    tnl = EXCLUDED.tnl;

/*
Statement 1
  - Backfill skills from legacy character columns
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
INSERT INTO "public"."skills" (char_id, name, rank, tnl)
SELECT id, 'Evasion', rank_evasion, tnl_evasion FROM "public"."characters"
ON CONFLICT (char_id, name) DO UPDATE
SET rank = EXCLUDED.rank,
    tnl = EXCLUDED.tnl;

/*
Statement 2
  - DELETES_DATA: Deletes all values in the column
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" DROP COLUMN "rank_evasion";

/*
Statement 3
  - DELETES_DATA: Deletes all values in the column
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" DROP COLUMN "rank_martial_arts";

/*
Statement 4
  - DELETES_DATA: Deletes all values in the column
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" DROP COLUMN "tnl_evasion";

/*
Statement 5
  - DELETES_DATA: Deletes all values in the column
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" DROP COLUMN "tnl_martial_arts";

/*
Statement 6
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."skills" ADD COLUMN "pending" real DEFAULT 0 NOT NULL;
