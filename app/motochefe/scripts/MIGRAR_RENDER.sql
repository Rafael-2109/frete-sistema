-- ============================================================================
-- MIGRAÇÃO: CONFIGURAÇÕES DE EQUIPE DE VENDAS - SISTEMA MOTOCHEFE
-- Data: 05/01/2025
-- Descrição: Adiciona campos de configuração em equipe_vendas_moto,
--            torna equipe obrigatória em vendedor_moto e remove
--            responsavel_movimentacao de pedido_venda_moto
-- ============================================================================

-- IMPORTANTE: Execute este script diretamente no PostgreSQL Shell do Render
-- Copie e cole TODO o conteúdo deste arquivo de uma vez

BEGIN;

-- ============================================================================
-- PARTE 1: ADICIONAR CAMPOS EM EQUIPE_VENDAS_MOTO
-- ============================================================================

-- Campo: Responsável Movimentação (RJ ou NACOM)
ALTER TABLE equipe_vendas_moto
ADD COLUMN IF NOT EXISTS responsavel_movimentacao VARCHAR(20);

-- Campo: Tipo de Comissão (FIXA_EXCEDENTE ou PERCENTUAL)
ALTER TABLE equipe_vendas_moto
ADD COLUMN IF NOT EXISTS tipo_comissao VARCHAR(20) DEFAULT 'FIXA_EXCEDENTE' NOT NULL;

-- Campo: Valor Comissão Fixa (para tipo FIXA_EXCEDENTE)
ALTER TABLE equipe_vendas_moto
ADD COLUMN IF NOT EXISTS valor_comissao_fixa NUMERIC(15, 2) DEFAULT 0 NOT NULL;

-- Campo: Percentual Comissão (para tipo PERCENTUAL)
ALTER TABLE equipe_vendas_moto
ADD COLUMN IF NOT EXISTS percentual_comissao NUMERIC(5, 2) DEFAULT 0 NOT NULL;

-- Campo: Comissão Rateada (TRUE = divide, FALSE = só vendedor do pedido)
ALTER TABLE equipe_vendas_moto
ADD COLUMN IF NOT EXISTS comissao_rateada BOOLEAN DEFAULT TRUE NOT NULL;

-- Comentários nas colunas
COMMENT ON COLUMN equipe_vendas_moto.responsavel_movimentacao IS 'Responsável pela movimentação: RJ ou NACOM';
COMMENT ON COLUMN equipe_vendas_moto.tipo_comissao IS 'Tipo de comissão: FIXA_EXCEDENTE ou PERCENTUAL';
COMMENT ON COLUMN equipe_vendas_moto.valor_comissao_fixa IS 'Valor fixo da comissão (usado em FIXA_EXCEDENTE)';
COMMENT ON COLUMN equipe_vendas_moto.percentual_comissao IS 'Percentual da comissão sobre venda (usado em PERCENTUAL). Ex: 5.00 = 5%';
COMMENT ON COLUMN equipe_vendas_moto.comissao_rateada IS 'TRUE: divide entre todos vendedores da equipe. FALSE: apenas vendedor do pedido';


-- ============================================================================
-- PARTE 2: TORNAR EQUIPE OBRIGATÓRIA EM VENDEDOR_MOTO
-- ============================================================================

-- Verificar se há vendedores sem equipe ANTES de tornar obrigatório
DO $$
DECLARE
    qtd_sem_equipe INTEGER;
BEGIN
    SELECT COUNT(*) INTO qtd_sem_equipe
    FROM vendedor_moto
    WHERE equipe_vendas_id IS NULL;

    IF qtd_sem_equipe > 0 THEN
        RAISE EXCEPTION 'ATENÇÃO: Existem % vendedor(es) SEM equipe! Defina uma equipe para todos os vendedores antes de executar esta migração.', qtd_sem_equipe;
    END IF;
END $$;

-- Tornar equipe_vendas_id obrigatório
ALTER TABLE vendedor_moto
ALTER COLUMN equipe_vendas_id SET NOT NULL;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_vendedor_equipe ON vendedor_moto(equipe_vendas_id);

-- Comentário
COMMENT ON COLUMN vendedor_moto.equipe_vendas_id IS 'Equipe do vendedor (OBRIGATÓRIO - todo vendedor DEVE ter equipe)';


-- ============================================================================
-- PARTE 3: REMOVER RESPONSAVEL_MOVIMENTACAO DE PEDIDO_VENDA_MOTO
-- ============================================================================

-- Verificar se há pedidos com este campo preenchido
DO $$
DECLARE
    qtd_com_valor INTEGER;
BEGIN
    SELECT COUNT(*) INTO qtd_com_valor
    FROM pedido_venda_moto
    WHERE responsavel_movimentacao IS NOT NULL;

    IF qtd_com_valor > 0 THEN
        RAISE NOTICE 'AVISO: % pedido(s) possuem responsavel_movimentacao preenchido. Estes valores serão perdidos.', qtd_com_valor;
    END IF;
END $$;

-- Remover coluna
ALTER TABLE pedido_venda_moto
DROP COLUMN IF EXISTS responsavel_movimentacao;


-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================

-- Verificar campos adicionados em equipe_vendas_moto
SELECT
    'equipe_vendas_moto' AS tabela,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'equipe_vendas_moto'
AND column_name IN (
    'responsavel_movimentacao',
    'tipo_comissao',
    'valor_comissao_fixa',
    'percentual_comissao',
    'comissao_rateada'
)
ORDER BY ordinal_position;

-- Verificar equipe_vendas_id em vendedor_moto
SELECT
    'vendedor_moto' AS tabela,
    column_name,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'vendedor_moto'
AND column_name = 'equipe_vendas_id';

-- Verificar remoção de responsavel_movimentacao em pedido_venda_moto
SELECT
    'pedido_venda_moto' AS tabela,
    COUNT(*) AS campo_existe
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto'
AND column_name = 'responsavel_movimentacao';


-- ============================================================================
-- COMMIT DA TRANSAÇÃO
-- ============================================================================

COMMIT;

-- ============================================================================
-- MENSAGEM FINAL
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'MIGRAÇÃO CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'ALTERAÇÕES REALIZADAS:';
    RAISE NOTICE '  1. ✓ 5 campos adicionados em equipe_vendas_moto';
    RAISE NOTICE '  2. ✓ equipe_vendas_id agora é obrigatório em vendedor_moto';
    RAISE NOTICE '  3. ✓ responsavel_movimentacao removido de pedido_venda_moto';
    RAISE NOTICE '';
    RAISE NOTICE 'PRÓXIMOS PASSOS:';
    RAISE NOTICE '  1. Reiniciar servidor Flask (se estiver rodando)';
    RAISE NOTICE '  2. Configurar cada equipe de vendas com suas regras';
    RAISE NOTICE '  3. Testar criação de vendedor (deve exigir equipe)';
    RAISE NOTICE '  4. Testar criação de pedido (número sequencial + sem movimentação)';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
END $$;
