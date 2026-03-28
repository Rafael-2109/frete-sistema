-- Migration: Tornar categoria_moto_id nullable em carvia_cotacao_motos
-- Fix: PYTHON-FLASK-AY (NotNullViolation quando modelo não tem categoria)
-- Data: 2026-03-28

ALTER TABLE carvia_cotacao_motos
    ALTER COLUMN categoria_moto_id DROP NOT NULL;
