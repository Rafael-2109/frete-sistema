-- Migration HORA 05: cache de latitude/longitude em hora_loja
-- Data: 2026-04-19
-- Descricao:
--   Cacheia coordenadas para nao re-chamar API de geocoding em cada render do mapa.
--   Google Geocoding API (se GOOGLE_MAPS_API_KEY no env) ou Nominatim OSM (fallback).
-- Idempotente: ADD COLUMN IF NOT EXISTS.
-- RISCO: baixo. Somente ADD COLUMN nullable.

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 7);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS longitude DECIMAL(10, 7);

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS geocodado_em TIMESTAMP;

ALTER TABLE hora_loja
    ADD COLUMN IF NOT EXISTS geocoding_provider VARCHAR(20);
    -- Valores: 'google', 'nominatim', 'manual'
