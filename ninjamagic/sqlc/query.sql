-- Accounts

-- name: UpsertAccount :one
INSERT INTO accounts (provider, subject, email)
VALUES ($1, $2, $3)
ON CONFLICT (provider, subject) DO UPDATE
  SET email = EXCLUDED.email
RETURNING id, provider, subject, email, created_at;

-- name: GetAccountByProviderSubject :one
SELECT id, provider, subject, email, created_at
FROM accounts
WHERE provider = $1 AND subject = $2
LIMIT 1;

-- name: GetAccountByID :one
SELECT id, provider, subject, email, created_at
FROM accounts
WHERE id = $1
LIMIT 1;

-- Characters

-- name: CreateCharacter :one
INSERT INTO characters (account_id, slot, name)
VALUES ($1, $2, $3)
RETURNING id, account_id, slot, name, created_at;

-- name: GetCharactersByAccount :many
SELECT id, account_id, slot, name, created_at
FROM characters
WHERE account_id = $1
ORDER BY slot;

-- name: DeleteCharacterByAccountSlot :exec
DELETE FROM characters
WHERE account_id = $1 AND slot = $2;

-- name: CountCharactersForAccount :one
SELECT COUNT(*)::bigint AS count
FROM characters
WHERE account_id = $1;

-- name: GetOpenSlotsForAccount :many
SELECT s.slot
FROM slots AS s
LEFT JOIN characters AS c
  ON c.account_id = $1 AND c.slot = s.slot
WHERE c.id IS NULL
ORDER BY 1;
