-- Migration: Adiciona coluna odoo_status na tabela recebimento_fisico
-- Descricao: Campo para armazenar o status do picking no Odoo (state do stock.picking)
-- Valores possiveis: 'draft', 'waiting', 'confirmed', 'assigned', 'done', 'cancel'
--
-- Executar no Shell do Render:
--   psql $DATABASE_URL -c "$(cat scripts/migrations/add_odoo_status_recebimento_fisico.sql)"
-- Ou copiar e colar o comando abaixo diretamente:

ALTER TABLE recebimento_fisico
ADD COLUMN IF NOT EXISTS odoo_status VARCHAR(20) DEFAULT NULL;
