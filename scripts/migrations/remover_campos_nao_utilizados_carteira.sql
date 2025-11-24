-- ===========================================
-- REMOVER CAMPOS NÃO UTILIZADOS DA CARTEIRA_PRINCIPAL
-- ===========================================
-- Data: 23/11/2025
-- Motivo: Campos nunca foram preenchidos (100% NULL ou vazio)
-- Para executar no Shell do Render
-- ===========================================

-- DADOS OPERACIONAIS (todos vazios ou apenas strings vazias '')
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS expedicao;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS agendamento;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS protocolo;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS roteirizacao;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS data_entrega;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS hora_agendamento;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS agendamento_confirmado;

-- VÍNCULO SEPARAÇÃO (não utilizado aqui - vínculo está em Separacao)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS separacao_lote_id;

-- ANÁLISE DE ESTOQUE (todos vazios)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS menor_estoque_produto_d7;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS saldo_estoque_pedido;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS saldo_estoque_pedido_forcado;

-- DADOS DE CARGA/LOTE (todos vazios - usamos Separacao para isso)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS qtd_saldo;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS valor_saldo;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS pallet;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS peso;

-- DADOS DE ROTA (todos vazios)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS rota;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS sub_rota;

-- TOTALIZADORES CLIENTE (todos vazios)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS valor_saldo_total;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS pallet_total;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS peso_total;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS valor_cliente_pedido;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS pallet_cliente_pedido;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS peso_cliente_pedido;

-- TOTALIZADORES PRODUTO (todos vazios)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS qtd_total_produto_carteira;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque;

-- PROJEÇÃO D0-D28 (28 campos - todos vazios)
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d0;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d1;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d2;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d3;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d4;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d5;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d6;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d7;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d8;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d9;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d10;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d11;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d12;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d13;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d14;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d15;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d16;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d17;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d18;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d19;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d20;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d21;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d22;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d23;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d24;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d25;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d26;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d27;
ALTER TABLE carteira_principal DROP COLUMN IF EXISTS estoque_d28;

-- ===========================================
-- VERIFICAÇÃO
-- ===========================================
SELECT 'Campos removidos com sucesso!' AS resultado;

-- Lista colunas restantes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'carteira_principal'
ORDER BY ordinal_position;
