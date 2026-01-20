/*
SCRIPT:
pg-schema-diff plan --from-dsn "postgres://postgres:postgres@localhost:5432/postgres" --to-dir ./ninjamagic/sqlc/schema.sql > ./migrations/items_inventories.sql
cat ./migrations/items_inventories.sql | docker exec -i db psql -U postgres

Statement 0
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE TABLE "public"."items" (
    "id" bigserial PRIMARY KEY,
    "name" citext NOT NULL,
    "spec" jsonb DEFAULT '[]'::jsonb NOT NULL,
    "created_at" timestamptz DEFAULT now() NOT NULL,
    "updated_at" timestamptz DEFAULT now() NOT NULL,
    UNIQUE ("name")
);

/*
Statement 1
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE TABLE "public"."inventories" (
    "id" bigserial PRIMARY KEY,
    "owner_id" bigint DEFAULT 0 NOT NULL,
    "item_id" bigint NOT NULL REFERENCES "public"."items" ("id") ON DELETE CASCADE,
    "slot" text DEFAULT '' NOT NULL,
    "container_id" bigint REFERENCES "public"."inventories" ("id") ON DELETE CASCADE,
    "map_id" integer,
    "x" integer,
    "y" integer,
    "instance_spec" jsonb,
    "created_at" timestamptz DEFAULT now() NOT NULL,
    "updated_at" timestamptz DEFAULT now() NOT NULL,
    CHECK (
        (
            "container_id" IS NOT NULL
            AND "map_id" IS NULL
            AND "x" IS NULL
            AND "y" IS NULL
        )
        OR (
            "container_id" IS NULL
            AND "map_id" IS NOT NULL
            AND "x" IS NOT NULL
            AND "y" IS NOT NULL
        )
    )
);

/*
Statement 2
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE INDEX "idx_inventories_owner" ON "public"."inventories" ("owner_id");

/*
Statement 3
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE INDEX "idx_inventories_map" ON "public"."inventories" ("map_id");

/*
Statement 4
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE INDEX "idx_inventories_container" ON "public"."inventories" ("container_id");

/*
Statement 5
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE INDEX "idx_inventories_item" ON "public"."inventories" ("item_id");
