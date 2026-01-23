/*
SCRIPT:
pg-schema-diff plan --from-dsn "postgres://postgres:postgres@localhost:5432/postgres" --to-dir ./ninjamagic/sqlc/schema.sql

Statement 0
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE SEQUENCE "public"."inventories_id_seq"
	AS bigint
	INCREMENT BY 1
	MINVALUE 1 MAXVALUE 9223372036854775807
	START WITH 1 CACHE 1 NO CYCLE
;

/*
Statement 1
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
CREATE TABLE "public"."inventories" (
	"eid" bigint NOT NULL,
	"owner_id" bigint,
	"id" bigint DEFAULT nextval('inventories_id_seq'::regclass) NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"container_eid" bigint,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"level" integer DEFAULT 0 NOT NULL,
	"map_id" integer,
	"x" integer,
	"y" integer,
	"key" text COLLATE "pg_catalog"."default" NOT NULL,
	"state" jsonb,
	"slot" text COLLATE "pg_catalog"."default" DEFAULT ''::text NOT NULL
);

/*
Statement 2
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories" ADD CONSTRAINT "inventories_location_check" CHECK((((container_eid IS NOT NULL) AND (map_id IS NULL) AND (owner_id IS NOT NULL)) OR ((container_eid IS NOT NULL) AND (map_id IS NULL) AND (owner_id IS NULL)) OR ((container_eid IS NULL) AND (map_id IS NOT NULL) AND (owner_id IS NULL)) OR ((container_eid IS NULL) AND (map_id IS NULL) AND (owner_id IS NOT NULL))));

/*
Statement 3
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories" ADD CONSTRAINT "inventories_owner_id_fkey" FOREIGN KEY (owner_id) REFERENCES characters(id) ON DELETE CASCADE NOT VALID;

/*
Statement 4
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories" VALIDATE CONSTRAINT "inventories_owner_id_fkey";

/*
Statement 5
*/
SET SESSION statement_timeout = 1200000;
SET SESSION lock_timeout = 3000;
CREATE UNIQUE INDEX CONCURRENTLY inventories_pkey ON public.inventories USING btree (id);

/*
Statement 6
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER TABLE "public"."inventories" ADD CONSTRAINT "inventories_pkey" PRIMARY KEY USING INDEX "inventories_pkey";

/*
Statement 7
*/
SET SESSION statement_timeout = 1200000;
SET SESSION lock_timeout = 3000;
CREATE INDEX CONCURRENTLY idx_inventories_map ON public.inventories USING btree (map_id);

/*
Statement 8
*/
SET SESSION statement_timeout = 1200000;
SET SESSION lock_timeout = 3000;
CREATE INDEX CONCURRENTLY idx_inventories_owner ON public.inventories USING btree (owner_id);

/*
Statement 9
*/
SET SESSION statement_timeout = 3000;
SET SESSION lock_timeout = 3000;
ALTER SEQUENCE "public"."inventories_id_seq" OWNED BY "public"."inventories"."id";
