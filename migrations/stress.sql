/*
SCRIPT:
brew install pg-schema-diff
pg-schema-diff plan --from-dsn "postgres://postgres:postgres@localhost:5432/postgres" --to-dir ./ninjamagic/sqlc/schema.sql > ./migrations/stress.sql
cat ./migrations/stress.sql | docker exec -i db psql -U postgres 

Statement 0
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" ADD COLUMN "aggravated_stress" real DEFAULT 0.0 NOT NULL;

/*
Statement 1
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" ADD COLUMN "stress" real DEFAULT 0.0 NOT NULL;
