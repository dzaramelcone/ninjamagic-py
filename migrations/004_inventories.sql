/*
Migration: Inventories table

Creates the inventories table for item instances in the world and player inventories.
Items are keyed by type string rather than referencing a template table.
*/

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
    level       INTEGER     NOT NULL DEFAULT 0,
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

-- Seed world items on DEMO map (map_id=2)
-- Note: DEMO is the second entity created after NOWHERE
INSERT INTO inventories (key, map_id, x, y, level) VALUES
    ('lily_pad', 2, 8, 11, 0),
    ('backpack', 2, 9, 4, 0),
    ('bedroll', 2, 9, 4, 10),
    ('broadsword', 2, 9, 4, 0);
