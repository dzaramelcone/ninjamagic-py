/*
SCRIPT:
pg-schema-diff plan --from-dsn "postgres://postgres:postgres@localhost:5432/postgres" --to-dir ./ninjamagic/sqlc/schema.sql > ./migrations/inventory_owner_constraint.sql
cat ./migrations/inventory_owner_constraint.sql | docker exec -i db psql -U postgres

Statement 0
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories" DROP CONSTRAINT IF EXISTS "inventories_check";

/*
Statement 1
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories" DROP CONSTRAINT IF EXISTS "inventories_container_id_check";

/*
Statement 2
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories"
ADD CONSTRAINT "inventories_location_check" CHECK (
    (
        "container_id" IS NOT NULL
        AND "map_id" IS NULL
        AND "x" IS NULL
        AND "y" IS NULL
        AND "owner_id" <> 0
    )
    OR (
        "container_id" IS NULL
        AND "map_id" IS NOT NULL
        AND "x" IS NOT NULL
        AND "y" IS NOT NULL
    )
    OR (
        "container_id" IS NULL
        AND "map_id" IS NULL
        AND "x" IS NULL
        AND "y" IS NULL
        AND "owner_id" <> 0
    )
);
