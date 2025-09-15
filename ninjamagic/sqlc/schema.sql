CREATE TYPE oauth_provider AS ENUM ('google', 'discord');
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS accounts (
    id              BIGSERIAL             PRIMARY KEY,
    owner_id        BIGSERIAL             NOT NULL,
    provider        oauth_provider        NOT NULL,
    subject         TEXT                  NOT NULL,
    email           CITEXT                NOT NULL,
    created_at      TIMESTAMPTZ           NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,

    UNIQUE (provider, subject)
);

CREATE TABLE IF NOT EXISTS characters (
    id          BIGSERIAL PRIMARY KEY,
    owner_id    BIGINT      NOT NULL,
    name        CITEXT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS skills (
    id          BIGSERIAL PRIMARY KEY,
    char_id     BIGINT    NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    name        CITEXT    NOT NULL,
    experience  BIGINT    NOT NULL DEFAULT 0,
    pending     BIGINT    NOT NULL DEFAULT 0,

    UNIQUE (char_id, name),
    CHECK (experience >= 0 AND pending >= 0)
);

CREATE INDEX IF NOT EXISTS idx_characters_owner ON characters(owner_id);
CREATE INDEX IF NOT EXISTS idx_accounts_owner ON accounts(owner_id);
CREATE INDEX IF NOT EXISTS idx_skills_char ON skills(char_id)
