-- Seed world items on DEMO map (map_id=2)
-- Note: DEMO is the second entity created after NOWHERE
TRUNCATE inventories RESTART IDENTITY;
INSERT INTO inventories
    (eid, key,          slot, container_eid, map_id, x,    y,    level, state) VALUES
    -- Ground items
    (1,   'lily_pad',   '',   NULL,          2,      8,    11,   0,     NULL),
    (2,   'backpack',   '',   NULL,          2,      9,    4,    0,     NULL),
    (3,   'bonfire',    '',   NULL,          2,      7,    7,    0,     NULL),
    (4,   'bedroll',    '',   NULL,          2,      9,    4,    10,    NULL),
    (5,   'broadsword', '',   NULL,          2,      9,    4,    0,     NULL),
    -- Nested: cookpot in backpack
    (6,   'cookpot',    '',   2,             NULL,   NULL, NULL, 0,     NULL),
    -- Nested: leeks in cookpot (3 levels deep)
    (7,   'leek',       '',   6,             NULL,   NULL, NULL, 0,     NULL),
    (8,   'leek',       '',   6,             NULL,   NULL, NULL, 0,     '[{"kind": "Noun", "value": "chive"}]');
