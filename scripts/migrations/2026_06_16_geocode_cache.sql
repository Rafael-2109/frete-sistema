CREATE TABLE IF NOT EXISTS geocode_cache (
    id               SERIAL PRIMARY KEY,
    endereco_hash    VARCHAR(32) NOT NULL,
    endereco         TEXT NOT NULL,
    lat              DOUBLE PRECISION NOT NULL,
    lng              DOUBLE PRECISION NOT NULL,
    fonte            VARCHAR(20) DEFAULT 'google',
    geocodificado_em TIMESTAMP,
    CONSTRAINT uq_geocode_cache_hash UNIQUE (endereco_hash)
);
CREATE INDEX IF NOT EXISTS ix_geocode_cache_hash ON geocode_cache (endereco_hash);
