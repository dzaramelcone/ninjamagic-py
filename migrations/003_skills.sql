/*
Statement 0
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE TABLE IF NOT EXISTS "public"."skills" (
    "id" bigserial PRIMARY KEY,
    "char_id" bigint NOT NULL REFERENCES "public"."characters"("id") ON DELETE CASCADE,
    "name" citext NOT NULL,
    "rank" bigint NOT NULL DEFAULT 0,
    "tnl" real NOT NULL DEFAULT 0,
    UNIQUE ("char_id", "name"),
    CHECK ("rank" >= 0 AND "tnl" >= 0)
);

/*
Statement 1
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
INSERT INTO "public"."skills" ("char_id", "name", "rank", "tnl")
SELECT "id", 'Martial Arts', "rank_martial_arts", "tnl_martial_arts" FROM "public"."characters"
ON CONFLICT ("char_id", "name") DO UPDATE
SET "rank" = EXCLUDED."rank",
    "tnl" = EXCLUDED."tnl";

/*
Statement 2
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
INSERT INTO "public"."skills" ("char_id", "name", "rank", "tnl")
SELECT "id", 'Evasion', "rank_evasion", "tnl_evasion" FROM "public"."characters"
ON CONFLICT ("char_id", "name") DO UPDATE
SET "rank" = EXCLUDED."rank",
    "tnl" = EXCLUDED."tnl";

/*
Statement 3
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
INSERT INTO "public"."skills" ("char_id", "name", "rank", "tnl")
SELECT "id", 'Survival', 0, 0 FROM "public"."characters"
ON CONFLICT ("char_id", "name") DO NOTHING;

/*
Statement 4
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."characters"
    DROP COLUMN IF EXISTS "rank_evasion",
    DROP COLUMN IF EXISTS "tnl_evasion",
    DROP COLUMN IF EXISTS "rank_martial_arts",
    DROP COLUMN IF EXISTS "tnl_martial_arts";
