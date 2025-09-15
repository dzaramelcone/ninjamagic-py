-- Accounts

-- name: UpsertIdentity :one
INSERT INTO accounts (owner_id, provider, subject, email, created_at, last_login_at)
VALUES (DEFAULT, $1, $2, $3, now(), now())
ON CONFLICT (provider, subject) DO UPDATE
  SET email = EXCLUDED.email,
      last_login_at = EXCLUDED.last_login_at
RETURNING owner_id;

-- Characters

-- name: GetCharacters :many
SELECT * FROM characters WHERE owner_id = $1 ORDER BY created_at DESC;

-- name: CreateCharacter :one
INSERT INTO characters (owner_id, name) VALUES ($1, $2) RETURNING *;

-- name: DeleteCharacter :exec
DELETE FROM characters WHERE id = $1;


-- Skills

-- name: GetSkillsByCharacter :many
SELECT * FROM skills WHERE char_id = $1;

-- name: UpsertSkills :exec
INSERT INTO skills (char_id, name, experience, pending)
SELECT
  $1::bigint,
  n.name,
  e.experience,
  p.pending
FROM unnest($2::citext[])  WITH ORDINALITY AS n(name, i)
JOIN unnest($3::bigint[])  WITH ORDINALITY AS e(experience, i) USING (i)
JOIN unnest($4::bigint[])  WITH ORDINALITY AS p(pending, i)    USING (i)
ON CONFLICT (char_id, name) DO UPDATE
SET experience = EXCLUDED.experience,
    pending    = EXCLUDED.pending;
