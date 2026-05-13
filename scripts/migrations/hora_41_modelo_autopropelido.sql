-- Migration HORA 41: campo `autopropelido` (Boolean) em hora_modelo
--
-- Objetivo: classificar cada modelo cadastrado entre "Autopropelido"
-- (bicicleta eletrica conforme Resolucao CONTRAN 996/2023 — dispensa CNH e
-- licenciamento) e "Ciclomotor" (exige CNH, emplacamento e ATPV em ate 15
-- dias uteis). Os textos correspondentes sao montados pelo PayloadBuilder
-- em `inf_contribuinte` na emissao da NF-e via TagPlus.
--
-- Default TRUE porque a HORA comercializa predominantemente bicicletas
-- eletricas; operador ajusta os ciclomotores caso a caso na tela de
-- edicao do modelo. NOT NULL para impedir registros novos sem
-- classificacao.
--
-- Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

ALTER TABLE hora_modelo
    ADD COLUMN IF NOT EXISTS autopropelido BOOLEAN NOT NULL DEFAULT TRUE;
