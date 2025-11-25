CREATE TYPE oauth_provider AS ENUM ('google', 'discord');
CREATE TYPE pronoun AS ENUM ('she','he','they','it');
CREATE TYPE stance AS ENUM ('standing', 'kneeling', 'sitting', 'lying prone');
CREATE TYPE condition AS ENUM ('normal', 'unconscious', 'in shock', 'dead');
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
    id          BIGSERIAL   PRIMARY KEY,
    owner_id    BIGINT      NOT NULL,

    -- Noun Component
    name        CITEXT      NOT NULL,
    pronoun     pronoun     NOT NULL,

    -- Glyph Component
    glyph       VARCHAR(1)  NOT NULL DEFAULT '@',
    
    -- Transform Component
    map_id      INTEGER     NOT NULL DEFAULT 2,
    x           INTEGER     NOT NULL DEFAULT 8,
    y           INTEGER     NOT NULL DEFAULT 8,
    
    -- Health Component
    health      REAL        NOT NULL DEFAULT 100.0,
    stress      REAL        NOT NULL DEFAULT 0.0,
    aggravated_stress  REAL NOT NULL DEFAULT 0.0,
    
    -- State Components
    stance      stance      NOT NULL DEFAULT 'standing',
    condition   condition   NOT NULL DEFAULT 'normal',
    
    -- Stats Component
    grace       INTEGER     NOT NULL DEFAULT 0,
    grit        INTEGER     NOT NULL DEFAULT 0,
    wit         INTEGER     NOT NULL DEFAULT 0,

    -- Skills Component
    rank_evasion      INTEGER    NOT NULL DEFAULT 0,
    tnl_evasion       REAL       NOT NULL DEFAULT 0,
    rank_martial_arts INTEGER    NOT NULL DEFAULT 0,
    tnl_martial_arts  REAL       NOT NULL DEFAULT 0,

    -- Auditing
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Constraints
    UNIQUE (name),
    UNIQUE (owner_id)
);


CREATE TABLE IF NOT EXISTS skills (
    id          BIGSERIAL PRIMARY KEY,
    char_id     BIGINT    NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    name        CITEXT    NOT NULL,
    rank        BIGINT    NOT NULL DEFAULT 0,
    tnl         REAL      NOT NULL DEFAULT 0,

    UNIQUE (char_id, name),
    CHECK (rank >= 0 AND tnl >= 0)
);

CREATE INDEX IF NOT EXISTS idx_characters_owner ON characters(owner_id);
CREATE INDEX IF NOT EXISTS idx_accounts_owner ON accounts(owner_id);
CREATE INDEX IF NOT EXISTS idx_skills_char ON skills(char_id);
