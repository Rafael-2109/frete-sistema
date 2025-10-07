"""
Script para adicionar campo modelo_rejeitado na tabela moto
Executar: python3 -m app.motochefe.scripts.adicionar_campo_modelo_rejeitado
"""
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campo_modelo_rejeitado():
    """Adiciona coluna modelo_rejeitado na tabela moto"""
    app = create_app()

    with app.app_context():
        try:
            
            # Adicionar a coluna
            print("📝 Adicionando coluna 'modelo_rejeitado'...")
            db.session.execute(text("""
                BEGIN;

                -- =====================================================
                -- 1. CRIAR TABELA TabelaPrecoEquipe
                -- =====================================================

                CREATE TABLE IF NOT EXISTS tabela_preco_equipe (
                    id SERIAL PRIMARY KEY,
                    equipe_vendas_id INTEGER NOT NULL REFERENCES equipe_vendas_moto(id) ON DELETE CASCADE,
                    modelo_id INTEGER NOT NULL REFERENCES modelo_moto(id) ON DELETE CASCADE,
                    preco_venda NUMERIC(15, 2) NOT NULL,

                    -- Auditoria
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    atualizado_em TIMESTAMP,
                    atualizado_por VARCHAR(100),
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,

                    -- Constraint de unicidade
                    CONSTRAINT uk_equipe_modelo_preco UNIQUE (equipe_vendas_id, modelo_id)
                );

                -- Índices
                CREATE INDEX IF NOT EXISTS idx_tabela_preco_equipe_equipe ON tabela_preco_equipe(equipe_vendas_id);
                CREATE INDEX IF NOT EXISTS idx_tabela_preco_equipe_modelo ON tabela_preco_equipe(modelo_id);

                -- Comentários
                COMMENT ON TABLE tabela_preco_equipe IS 'Tabela de preços específicos por Equipe x Modelo';
                COMMENT ON COLUMN tabela_preco_equipe.preco_venda IS 'Preço de venda para este modelo nesta equipe';

                -- =====================================================
                -- 2. ADICIONAR CAMPOS EM EquipeVendasMoto
                -- =====================================================

                -- Campos de Movimentação
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS custo_movimentacao NUMERIC(15, 2) DEFAULT 0 NOT NULL;

                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS incluir_custo_movimentacao BOOLEAN DEFAULT FALSE NOT NULL;

                -- Campos de Precificação
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS tipo_precificacao VARCHAR(20) DEFAULT 'TABELA' NOT NULL;

                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS markup NUMERIC(15, 2) DEFAULT 0 NOT NULL;

                -- Campo de Montagem
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS permitir_montagem BOOLEAN DEFAULT TRUE NOT NULL;

                -- Comentários
                COMMENT ON COLUMN equipe_vendas_moto.custo_movimentacao IS 'Custo específico de movimentação desta equipe';
                COMMENT ON COLUMN equipe_vendas_moto.incluir_custo_movimentacao IS 'TRUE: adiciona custo ao preço final | FALSE: já incluído na tabela';
                COMMENT ON COLUMN equipe_vendas_moto.tipo_precificacao IS 'TABELA: usa TabelaPrecoEquipe | CUSTO_MARKUP: custo_aquisicao + markup';
                COMMENT ON COLUMN equipe_vendas_moto.markup IS 'Valor fixo adicionado ao custo quando tipo_precificacao=CUSTO_MARKUP';
                COMMENT ON COLUMN equipe_vendas_moto.permitir_montagem IS 'TRUE: exibe campos de montagem no formulário | FALSE: oculta e força montagem=False';

                -- =====================================================
                -- 3. REMOVER CAMPOS OBSOLETOS DE CustosOperacionais
                -- =====================================================

                -- IMPORTANTE: Esses campos serão dropados, então capture os dados antes se necessário
                -- Criar backup temporário (opcional)
                DO $$
                BEGIN
                    -- Se existir algum registro com valores nesses campos, avisar no log
                    IF EXISTS (SELECT 1 FROM custos_operacionais WHERE custo_movimentacao_rj > 0 OR custo_movimentacao_nacom > 0 OR valor_comissao_fixa > 0) THEN
                        RAISE NOTICE 'AVISO: Existem valores em custos_operacionais que serão perdidos. Execute backup antes se necessário.';
                    END IF;
                END $$;

                -- Dropar colunas (se existirem)
                ALTER TABLE custos_operacionais
                DROP COLUMN IF EXISTS custo_movimentacao_rj;

                ALTER TABLE custos_operacionais
                DROP COLUMN IF EXISTS custo_movimentacao_nacom;

                ALTER TABLE custos_operacionais
                DROP COLUMN IF EXISTS valor_comissao_fixa;

                -- =====================================================
                -- 4. VERIFICAÇÕES FINAIS
                -- =====================================================

                -- Verificar se as colunas foram adicionadas
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'equipe_vendas_moto' AND column_name = 'custo_movimentacao') THEN
                        RAISE EXCEPTION 'ERRO: Coluna custo_movimentacao não foi criada em equipe_vendas_moto';
                    END IF;

                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'equipe_vendas_moto' AND column_name = 'tipo_precificacao') THEN
                        RAISE EXCEPTION 'ERRO: Coluna tipo_precificacao não foi criada em equipe_vendas_moto';
                    END IF;

                    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tabela_preco_equipe') THEN
                        RAISE EXCEPTION 'ERRO: Tabela tabela_preco_equipe não foi criada';
                    END IF;

                    RAISE NOTICE 'SUCESSO: Todas as alterações foram aplicadas corretamente!';
                END $$;

                COMMIT;
            """))

            db.session.commit()
            print("✅ Coluna 'modelo_rejeitado' adicionada com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar coluna: {str(e)}")
            raise

if __name__ == '__main__':
    adicionar_campo_modelo_rejeitado()
