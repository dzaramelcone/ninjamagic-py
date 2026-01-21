/*
Migration: Items and inventories tables

Creates the items table (for item templates) and inventories table
(for item instances in the world and player inventories).
*/

-- Items table for item templates
CREATE TABLE IF NOT EXISTS items (
    id          BIGSERIAL   PRIMARY KEY,
    name        CITEXT      NOT NULL,
    spec        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (name)
);

-- Inventories table for item instances
CREATE TABLE IF NOT EXISTS inventories (
    id          BIGSERIAL   PRIMARY KEY,
    owner_id    BIGINT      REFERENCES characters(id) ON DELETE CASCADE,
    key         TEXT        NOT NULL,
    slot        TEXT        NOT NULL DEFAULT '',
    container_id BIGINT     REFERENCES inventories(id) ON DELETE CASCADE,
    map_id      INTEGER,
    x           INTEGER,
    y           INTEGER,
    state       JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT inventories_location_check CHECK (
        (
            container_id IS NOT NULL
            AND map_id IS NULL
            AND x IS NULL
            AND y IS NULL
            AND owner_id IS NOT NULL
        )
        OR
        (
            container_id IS NULL
            AND map_id IS NOT NULL
            AND x IS NOT NULL
            AND y IS NOT NULL
            AND owner_id IS NULL
        )
        OR
        (
            container_id IS NULL
            AND map_id IS NULL
            AND x IS NULL
            AND y IS NULL
            AND owner_id IS NOT NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_inventories_owner ON inventories(owner_id);
CREATE INDEX IF NOT EXISTS idx_inventories_map ON inventories(map_id);
CREATE INDEX IF NOT EXISTS idx_inventories_container ON inventories(container_id);
CREATE INDEX IF NOT EXISTS idx_inventories_key ON inventories(key);
