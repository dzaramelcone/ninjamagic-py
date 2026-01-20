-- Accounts

-- name: UpsertIdentity :one
INSERT INTO accounts (owner_id, provider, subject, email, created_at, last_login_at)
VALUES (DEFAULT, $1, $2, $3, now(), now())
ON CONFLICT (provider, subject) DO UPDATE
  SET email = EXCLUDED.email,
      last_login_at = EXCLUDED.last_login_at
RETURNING owner_id;

-- Characters

-- name: GetCharacterBrief :one
SELECT id, owner_id, name FROM characters WHERE owner_id = $1;

-- name: GetCharacter :one
SELECT * FROM characters c WHERE c.owner_id = $1;

-- name: CreateCharacter :one
INSERT INTO characters (owner_id, name, pronoun) VALUES ($1, $2, $3) RETURNING *;

-- name: DeleteCharacter :exec
DELETE FROM characters WHERE id = $1;

-- name: UpdateCharacter :exec
UPDATE characters
SET
  glyph = coalesce(sqlc.narg('glyph'), glyph),
  glyph_h = coalesce(sqlc.narg('glyph_h'), glyph_h),
  glyph_v = coalesce(sqlc.narg('glyph_v'), glyph_v),
  glyph_s = coalesce(sqlc.narg('glyph_s'), glyph_s),
  pronoun = coalesce(sqlc.narg('pronoun'), pronoun),
  map_id = coalesce(sqlc.narg('map_id'), map_id),
  x = coalesce(sqlc.narg('x'), x),
  y = coalesce(sqlc.narg('y'), y),
  health = coalesce(sqlc.narg('health'), health),
  stress = coalesce(sqlc.narg('stress'), stress),
  aggravated_stress = coalesce(sqlc.narg('aggravated_stress'), aggravated_stress),
  stance = coalesce(sqlc.narg('stance'), stance),
  condition = coalesce(sqlc.narg('condition'), condition),
  grace = coalesce(sqlc.narg('grace'), grace),
  grit = coalesce(sqlc.narg('grit'), grit),
  wit = coalesce(sqlc.narg('wit'), wit),
  updated_at = now()
WHERE id = $1;

-- Skills

-- name: GetSkillsForCharacter :many
SELECT * FROM skills WHERE char_id = sqlc.arg('char_id');

-- name: UpsertSkill :exec
INSERT INTO skills (char_id, name, rank, tnl, pending)
VALUES (
  sqlc.arg('char_id'),
  sqlc.arg('name'),
  sqlc.arg('rank'),
  sqlc.arg('tnl'),
  sqlc.arg('pending')
)
ON CONFLICT (char_id, name) DO UPDATE
SET rank = EXCLUDED.rank,
    tnl = EXCLUDED.tnl,
    pending = EXCLUDED.pending;

-- name: UpsertSkills :exec
INSERT INTO skills (char_id, name, rank, tnl, pending)
SELECT
  sqlc.arg('char_id'),
  unnest(sqlc.arg('names')::text[]),
  unnest(sqlc.arg('ranks')::bigint[]),
  unnest(sqlc.arg('tnls')::real[]),
  unnest(sqlc.arg('pendings')::real[])
ON CONFLICT (char_id, name) DO UPDATE
SET rank = EXCLUDED.rank,
    tnl = EXCLUDED.tnl,
    pending = EXCLUDED.pending;

-- Items + Inventories

-- name: GetInventoriesForOwner :many
SELECT * FROM inventories WHERE owner_id = $1;

-- name: GetInventoriesForMap :many
SELECT * FROM inventories WHERE map_id = $1;

-- name: GetItemsByIds :many
SELECT * FROM items WHERE id = ANY($1::bigint[]);

-- name: UpsertItemByName :one
INSERT INTO items (name, spec)
VALUES ($1, $2)
ON CONFLICT (name) DO UPDATE
  SET spec = EXCLUDED.spec,
      updated_at = now()
RETURNING id;

-- name: DeleteInventoriesForOwner :exec
DELETE FROM inventories WHERE owner_id = $1;

-- name: InsertInventoriesForOwner :exec
INSERT INTO inventories (id, owner_id, item_id, slot, container_id, map_id, x, y, instance_spec)
SELECT
  unnest(sqlc.arg('ids')::bigint[]),
  unnest(sqlc.arg('owner_ids')::bigint[]),
  unnest(sqlc.arg('item_ids')::bigint[]),
  unnest(sqlc.arg('slots')::text[]),
  NULLIF(unnest(sqlc.arg('container_ids')::bigint[]), 0),
  NULLIF(unnest(sqlc.arg('map_ids')::integer[]), -1),
  NULLIF(unnest(sqlc.arg('xs')::integer[]), -1),
  NULLIF(unnest(sqlc.arg('ys')::integer[]), -1),
  unnest(sqlc.arg('instance_specs')::jsonb[]);

-- name: DeleteInventoryById :exec
DELETE FROM inventories WHERE id = $1;
