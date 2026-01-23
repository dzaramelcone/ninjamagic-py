-- Seed world items on DEMO map (map_id=2)
-- Note: DEMO is the second entity created after NOWHERE
TRUNCATE inventories RESTART IDENTITY;
INSERT INTO inventories
    (eid, key,          slot, container_eid, map_id, x,    y,    level) VALUES
    (1,   'lily_pad',   '',   NULL,          2,      8,    11,   0),
    (2,   'backpack',   '',   NULL,          2,      9,    4,    0),
    (3,   'cookpot',    '',   2,             NULL,   NULL, NULL, 0),
    (4,   'bedroll',    '',   NULL,          2,      9,    4,    10),
    (5,   'broadsword', '',   NULL,          2,      9,    4,    0);
