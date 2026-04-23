-- Migration: adiciona coluna TeamsTask.resposta_card JSONB
-- Permite ao agente retornar cards Adaptive estruturados (nao apenas texto).
-- A Azure Function bot.py detecta este campo no polling e renderiza via builders.
-- Idempotente: IF NOT EXISTS.

ALTER TABLE teams_tasks
    ADD COLUMN IF NOT EXISTS resposta_card JSONB;

COMMENT ON COLUMN teams_tasks.resposta_card IS
    'Card Adaptive estruturado retornado pelo agente (JSONB). Quando presente, bot.py renderiza via build_<template>_card. Formato: {template: str, data: dict}.';
