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
  glyph = COALESCE($2, glyph),
  pronoun = COALESCE($3, pronoun),
  map_id = COALESCE($4, map_id),
  x = COALESCE($5, x),
  y = COALESCE($6, y),
  health = COALESCE($7, health),
  stance = COALESCE($8, stance),
  condition = COALESCE($9, condition),
  grace = COALESCE($10, grace),
  grit = COALESCE($11, grit),
  wit = COALESCE($12, wit),
  rank_martial_arts = COALESCE($13, rank_martial_arts),
  tnl_martial_arts = COALESCE($14, tnl_martial_arts),
  rank_evasion = COALESCE($15, rank_evasion),
  tnl_evasion = COALESCE($16, tnl_evasion),
  updated_at = now()
WHERE id = $1;
