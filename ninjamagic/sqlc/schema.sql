CREATE TABLE IF NOT EXISTS accounts (
    id          BIGSERIAL PRIMARY KEY,
    provider    TEXT        NOT NULL CHECK (provider IN ('google','discord')),
    subject     TEXT        NOT NULL,
    email       TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, subject)
);

CREATE TABLE IF NOT EXISTS slots (
    slot SMALLINT PRIMARY KEY
);

INSERT INTO slots(slot) VALUES (0) ON CONFLICT DO NOTHING;
INSERT INTO slots(slot) VALUES (1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS characters (
    id          BIGSERIAL PRIMARY KEY,
    account_id  BIGINT      NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    slot        SMALLINT    NOT NULL REFERENCES slots(slot),
    name        TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, slot)
);

CREATE INDEX IF NOT EXISTS idx_characters_account ON characters(account_id);
