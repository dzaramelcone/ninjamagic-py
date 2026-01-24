-- Seed world items on DEMO map (map_id=2)
-- Note: DEMO is the second entity created after NOWHERE
TRUNCATE inventories RESTART IDENTITY;
INSERT INTO inventories
    (eid, key,          slot, container_eid, map_id, x,    y,    level, state) VALUES
    -- Ground items
    (1,   'prop',       '',   NULL,          2,      8,    11,   0,     '{"noun": {"value": "lily pad"}, "glyph": {"char": "ო", "h": 0.33, "s": 0.6, "v": 0.6}}'),
    (2,   'backpack',   '',   NULL,          2,      9,    4,    0,     NULL),
    (3,   'bonfire',    '',   NULL,          2,      4,    9,    0,     NULL),
    (4,   'bedroll',    '',   NULL,          2,      9,    4,    10,    NULL),
    (5,   'broadsword', '',   NULL,          2,      9,    4,    0,     NULL),
    -- Nested: cookpot in backpack
    (6,   'cookpot',    '',   2,             NULL,   NULL, NULL, 0,     NULL),
    -- Nested: forages in cookpot (3 levels deep)
    (7,   'forage',     '',   6,             NULL,   NULL, NULL, 0,     NULL),
    (8,   'forage',     '',   6,             NULL,   NULL, NULL, 0,     '{"noun": {"value": "chive"}}');
