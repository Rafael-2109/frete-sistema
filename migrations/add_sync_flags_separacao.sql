-- Script de migração para adicionar flags de controle de sincronização na tabela Separacao
-- Data: 2025-08-21
-- Objetivo: Permitir rastreamento de sincronização entre NF e Separação

-- Adicionar campos de controle de sincronização
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS sincronizado_nf BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20),
ADD COLUMN IF NOT EXISTS data_sincronizacao TIMESTAMP,
ADD COLUMN IF NOT EXISTS zerado_por_sync BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS data_zeragem TIMESTAMP;

-- Adicionar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_separacao_sincronizado_nf ON separacao(sincronizado_nf);
CREATE INDEX IF NOT EXISTS idx_separacao_numero_nf ON separacao(numero_nf);
CREATE INDEX IF NOT EXISTS idx_separacao_zerado_por_sync ON separacao(zerado_por_sync);

-- Comentários explicativos
COMMENT ON COLUMN separacao.sincronizado_nf IS 'Indica se a separação foi sincronizada com uma NF faturada';
COMMENT ON COLUMN separacao.numero_nf IS 'Número da NF associada quando sincronizada';
COMMENT ON COLUMN separacao.data_sincronizacao IS 'Data/hora da última sincronização com NF';
COMMENT ON COLUMN separacao.zerado_por_sync IS 'Indica se foi zerada pelo processo de sincronização com Odoo';
COMMENT ON COLUMN separacao.data_zeragem IS 'Data/hora quando foi zerada pela sincronização';