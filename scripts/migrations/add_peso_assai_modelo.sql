-- Migration: adicionar peso_kg + peso_cubado_kg em assai_modelo
-- Data: 2026-05-11
-- Descricao: Permite cadastrar peso fisico e peso cubado de cada modelo de moto Assai.
--   peso_cubado_kg sera usado no calculo de frete (motos vao MONTADAS — ocupam muito mais espaco).
--   peso_kg e usado em relatorios e portaria.
-- Idempotente: usa IF NOT EXISTS.

ALTER TABLE assai_modelo ADD COLUMN IF NOT EXISTS peso_kg NUMERIC(8, 2);
ALTER TABLE assai_modelo ADD COLUMN IF NOT EXISTS peso_cubado_kg NUMERIC(8, 2);
