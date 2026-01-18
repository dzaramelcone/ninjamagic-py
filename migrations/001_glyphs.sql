/*
pg-schema-diff plan --from-dsn "postgres://postgres:postgres@localhost:5432/postgres" --to-dir ./ninjamagic/sqlc/schema.sql > ./migrations/glyphs.sql
cat ./migrations/glyphs.sql | docker exec -i db psql -U postgres 

Statement 0
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" ADD COLUMN "glyph_h" real DEFAULT '0.5833'::real NOT NULL;

/*
Statement 1
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" ADD COLUMN "glyph_s" real DEFAULT '0.7'::real NOT NULL;

/*
Statement 2
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters" ADD COLUMN "glyph_v" real DEFAULT '0.828'::real NOT NULL;
