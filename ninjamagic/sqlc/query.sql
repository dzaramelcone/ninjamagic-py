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
  glyph = $2,
  pronoun = $3,
  map_id = $4,
  x = $5,
  y = $6,
  health = $7,
  stance = $8,
  condition = $9,
  grace = $10,
  grit = $11,
  wit = $12,
  rank_martial_arts = $13,
  tnl_martial_arts = $14,
  rank_evasion = $15,
  tnl_evasion = $16,
  updated_at = now()
WHERE id = $1;
