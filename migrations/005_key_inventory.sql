/*
Migration: Key-based inventory schema

Changes:
- Add key TEXT NOT NULL (populated from items.name)
- Make owner_id BIGINT NULL with FK to characters
- Rename instance_spec to state
- Drop item_id column and FK
- Update check constraint for owner_id NULL on world items
*/

-- Step 1: Add key column populated from items.name
ALTER TABLE inventories ADD COLUMN key TEXT;
UPDATE inventories SET key = (SELECT name FROM items WHERE items.id = inventories.item_id);
ALTER TABLE inventories ALTER COLUMN key SET NOT NULL;

-- Step 2: Make owner_id nullable and add FK to characters
-- First drop the NOT NULL and default, then add FK
ALTER TABLE inventories ALTER COLUMN owner_id DROP NOT NULL;
ALTER TABLE inventories ALTER COLUMN owner_id DROP DEFAULT;
-- Convert owner_id=0 to NULL for world items
UPDATE inventories SET owner_id = NULL WHERE owner_id = 0;
-- Add FK constraint
ALTER TABLE inventories ADD CONSTRAINT inventories_owner_id_fkey
    FOREIGN KEY (owner_id) REFERENCES characters(id) ON DELETE CASCADE;

-- Step 3: Rename instance_spec to state
ALTER TABLE inventories RENAME COLUMN instance_spec TO state;

-- Step 4: Drop item_id column and FK
ALTER TABLE inventories DROP CONSTRAINT IF EXISTS inventories_item_id_fkey;
ALTER TABLE inventories DROP COLUMN item_id;

-- Step 5: Drop old constraint and add new one
ALTER TABLE inventories DROP CONSTRAINT IF EXISTS inventories_location_check;
ALTER TABLE inventories ADD CONSTRAINT inventories_location_check CHECK (
    (
        container_id IS NOT NULL
        AND map_id IS NULL
        AND x IS NULL
        AND y IS NULL
        AND owner_id IS NOT NULL
    )
    OR (
        container_id IS NULL
        AND map_id IS NOT NULL
        AND x IS NOT NULL
        AND y IS NOT NULL
        AND owner_id IS NULL
    )
    OR (
        container_id IS NULL
        AND map_id IS NULL
        AND x IS NULL
        AND y IS NULL
        AND owner_id IS NOT NULL
    )
);

-- Step 6: Update indexes
DROP INDEX IF EXISTS idx_inventories_item;
CREATE INDEX IF NOT EXISTS idx_inventories_key ON inventories(key);
