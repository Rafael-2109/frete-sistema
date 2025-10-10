"""
Migration Completa - Sistema MotoChefe
Data: 08/01/2025

OBJETIVO: Sincronizar banco LOCAL com todas as alterações aplicadas no RENDER

INCLUI:
1. MIGRATION_SQL_RENDER.sql (CrossDocking e Parcelamento)
2. 20250106_alteracoes_precificacao_equipes.sql (Precificação por Equipe)
3. add_empresa_pagadora_embarque.sql (Pagamento de Frete)
4. Outros campos adicionados

INSTRUÇÕES:
1. Certifique-se de ter backup do banco
2. Execute: python app/motochefe/scripts/migration_completa_local.py
3. Verifique os logs para confirmar sucesso
"""

import sys
import os

# Adicionar caminho do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

app = create_app()

def executar_sql(sql, descricao):
    """Executa SQL e trata erros"""
    try:
        print(f"\n🔄 {descricao}...")
        db.session.execute(text(sql))
        db.session.commit()
        print(f"✅ {descricao} - SUCESSO")
        return True
    except Exception as e:
        print(f"❌ {descricao} - ERRO: {str(e)}")
        db.session.rollback()
        return False


def migration_crossdocking():
    """1. CrossDocking e Parcelamento (MIGRATION_SQL_RENDER.sql)"""
    print("\n" + "="*70)
    print("1️⃣  CROSSDOCKING E PARCELAMENTO")
    print("="*70)

    # 1.1 Criar tabela cross_docking
    sql = """
    CREATE TABLE IF NOT EXISTS cross_docking (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL UNIQUE,
        descricao TEXT,

        -- Movimentação
        responsavel_movimentacao VARCHAR(20),
        custo_movimentacao NUMERIC(15, 2) DEFAULT 0 NOT NULL,
        incluir_custo_movimentacao BOOLEAN DEFAULT FALSE NOT NULL,

        -- Precificação
        tipo_precificacao VARCHAR(20) DEFAULT 'TABELA' NOT NULL,
        markup NUMERIC(15, 2) DEFAULT 0 NOT NULL,

        -- Comissão
        tipo_comissao VARCHAR(20) DEFAULT 'FIXA_EXCEDENTE' NOT NULL,
        valor_comissao_fixa NUMERIC(15, 2) DEFAULT 0 NOT NULL,
        percentual_comissao NUMERIC(5, 2) DEFAULT 0 NOT NULL,
        comissao_rateada BOOLEAN DEFAULT TRUE NOT NULL,

        -- Montagem
        permitir_montagem BOOLEAN DEFAULT TRUE NOT NULL,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP,
        atualizado_por VARCHAR(100),
        ativo BOOLEAN DEFAULT TRUE NOT NULL
    );
    """
    executar_sql(sql, "Criar tabela cross_docking")

    # 1.2 Criar tabela tabela_preco_crossdocking
    sql = """
    CREATE TABLE IF NOT EXISTS tabela_preco_crossdocking (
        id SERIAL PRIMARY KEY,
        crossdocking_id INTEGER NOT NULL REFERENCES cross_docking(id),
        modelo_id INTEGER NOT NULL REFERENCES modelo_moto(id),
        preco_venda NUMERIC(15, 2) NOT NULL,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP,
        atualizado_por VARCHAR(100),
        ativo BOOLEAN DEFAULT TRUE NOT NULL,

        -- Constraint única
        CONSTRAINT uk_crossdocking_modelo_preco UNIQUE (crossdocking_id, modelo_id)
    );

    CREATE INDEX IF NOT EXISTS idx_tabela_preco_cd_crossdocking ON tabela_preco_crossdocking(crossdocking_id);
    CREATE INDEX IF NOT EXISTS idx_tabela_preco_cd_modelo ON tabela_preco_crossdocking(modelo_id);
    """
    executar_sql(sql, "Criar tabela tabela_preco_crossdocking")

    # 1.3 Adicionar campos em cliente_moto
    sql = """
    ALTER TABLE cliente_moto
    ADD COLUMN IF NOT EXISTS vendedor_id INTEGER REFERENCES vendedor_moto(id);

    ALTER TABLE cliente_moto
    ADD COLUMN IF NOT EXISTS crossdocking BOOLEAN DEFAULT FALSE NOT NULL;

    ALTER TABLE cliente_moto
    ADD COLUMN IF NOT EXISTS crossdocking_id INTEGER REFERENCES cross_docking(id);

    CREATE INDEX IF NOT EXISTS idx_cliente_moto_vendedor ON cliente_moto(vendedor_id);
    CREATE INDEX IF NOT EXISTS idx_cliente_moto_crossdocking ON cliente_moto(crossdocking_id);
    """
    executar_sql(sql, "Adicionar campos em cliente_moto (vendedor_id, crossdocking, crossdocking_id)")

    # 1.4 Adicionar campos em equipe_vendas_moto
    sql = """
    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS permitir_prazo BOOLEAN DEFAULT FALSE NOT NULL;

    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS permitir_parcelamento BOOLEAN DEFAULT FALSE NOT NULL;
    """
    executar_sql(sql, "Adicionar campos em equipe_vendas_moto (permitir_prazo, permitir_parcelamento)")

    # 1.5 Adicionar campos em pedido_venda_moto
    sql = """
    ALTER TABLE pedido_venda_moto
    ADD COLUMN IF NOT EXISTS prazo_dias INTEGER DEFAULT 0 NOT NULL;

    ALTER TABLE pedido_venda_moto
    ADD COLUMN IF NOT EXISTS numero_parcelas INTEGER DEFAULT 1 NOT NULL;
    """
    executar_sql(sql, "Adicionar campos em pedido_venda_moto (prazo_dias, numero_parcelas)")


def migration_precificacao_equipes():
    """2. Precificação por Equipe (20250106_alteracoes_precificacao_equipes.sql)"""
    print("\n" + "="*70)
    print("2️⃣  PRECIFICAÇÃO POR EQUIPE")
    print("="*70)

    # 2.1 Criar tabela tabela_preco_equipe
    sql = """
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

    CREATE INDEX IF NOT EXISTS idx_tabela_preco_equipe_equipe ON tabela_preco_equipe(equipe_vendas_id);
    CREATE INDEX IF NOT EXISTS idx_tabela_preco_equipe_modelo ON tabela_preco_equipe(modelo_id);

    COMMENT ON TABLE tabela_preco_equipe IS 'Tabela de preços específicos por Equipe x Modelo';
    COMMENT ON COLUMN tabela_preco_equipe.preco_venda IS 'Preço de venda para este modelo nesta equipe';
    """
    executar_sql(sql, "Criar tabela tabela_preco_equipe")

    # 2.2 Adicionar campos em equipe_vendas_moto
    sql = """
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
    """
    executar_sql(sql, "Adicionar campos de precificação em equipe_vendas_moto")

    # 2.3 Remover campos obsoletos de custos_operacionais
    sql = """
    ALTER TABLE custos_operacionais
    DROP COLUMN IF EXISTS custo_movimentacao_rj;

    ALTER TABLE custos_operacionais
    DROP COLUMN IF EXISTS custo_movimentacao_nacom;

    ALTER TABLE custos_operacionais
    DROP COLUMN IF EXISTS valor_comissao_fixa;
    """
    executar_sql(sql, "Remover campos obsoletos de custos_operacionais")


def migration_frete_embarque():
    """3. Pagamento de Frete Embarque (add_empresa_pagadora_embarque.sql)"""
    print("\n" + "="*70)
    print("3️⃣  PAGAMENTO DE FRETE EMBARQUE")
    print("="*70)

    sql = """
    -- Adicionar coluna empresa_pagadora_id
    ALTER TABLE embarque_moto
    ADD COLUMN IF NOT EXISTS empresa_pagadora_id INTEGER;

    -- Adicionar Foreign Key
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_embarque_empresa_pagadora'
        ) THEN
            ALTER TABLE embarque_moto
            ADD CONSTRAINT fk_embarque_empresa_pagadora
            FOREIGN KEY (empresa_pagadora_id)
            REFERENCES empresa_venda_moto(id);
        END IF;
    END $$;

    -- Adicionar Índice
    CREATE INDEX IF NOT EXISTS ix_embarque_moto_empresa_pagadora_id
    ON embarque_moto(empresa_pagadora_id);

    -- Comentário
    COMMENT ON COLUMN embarque_moto.empresa_pagadora_id IS 'Empresa que pagou o frete (FK para empresa_venda_moto)';
    """
    executar_sql(sql, "Adicionar empresa_pagadora_id em embarque_moto")


def verificacao_final():
    """Verificação final de todas as alterações"""
    print("\n" + "="*70)
    print("4️⃣  VERIFICAÇÃO FINAL")
    print("="*70)

    verificacoes = [
        ("Tabela cross_docking", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='cross_docking'", 1),
        ("Tabela tabela_preco_crossdocking", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='tabela_preco_crossdocking'", 1),
        ("Tabela tabela_preco_equipe", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='tabela_preco_equipe'", 1),
        ("Campo cliente_moto.vendedor_id", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='cliente_moto' AND column_name='vendedor_id'", 1),
        ("Campo cliente_moto.crossdocking", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='cliente_moto' AND column_name='crossdocking'", 1),
        ("Campo cliente_moto.crossdocking_id", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='cliente_moto' AND column_name='crossdocking_id'", 1),
        ("Campo equipe_vendas_moto.permitir_prazo", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='equipe_vendas_moto' AND column_name='permitir_prazo'", 1),
        ("Campo equipe_vendas_moto.permitir_parcelamento", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='equipe_vendas_moto' AND column_name='permitir_parcelamento'", 1),
        ("Campo equipe_vendas_moto.custo_movimentacao", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='equipe_vendas_moto' AND column_name='custo_movimentacao'", 1),
        ("Campo equipe_vendas_moto.tipo_precificacao", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='equipe_vendas_moto' AND column_name='tipo_precificacao'", 1),
        ("Campo pedido_venda_moto.prazo_dias", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='pedido_venda_moto' AND column_name='prazo_dias'", 1),
        ("Campo pedido_venda_moto.numero_parcelas", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='pedido_venda_moto' AND column_name='numero_parcelas'", 1),
        ("Campo embarque_moto.empresa_pagadora_id", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='embarque_moto' AND column_name='empresa_pagadora_id'", 1),
    ]

    erros = []
    sucessos = 0

    for descricao, query, esperado in verificacoes:
        try:
            resultado = db.session.execute(text(query)).scalar()
            if resultado == esperado:
                print(f"✅ {descricao}")
                sucessos += 1
            else:
                print(f"❌ {descricao} - Esperado: {esperado}, Encontrado: {resultado}")
                erros.append(descricao)
        except Exception as e:
            print(f"❌ {descricao} - ERRO: {str(e)}")
            erros.append(descricao)

    print("\n" + "="*70)
    print(f"📊 RESULTADO FINAL: {sucessos}/{len(verificacoes)} verificações passaram")
    print("="*70)

    if erros:
        print("\n⚠️  ATENÇÃO: As seguintes verificações falharam:")
        for erro in erros:
            print(f"   - {erro}")
        return False
    else:
        print("\n✅ TODAS AS VERIFICAÇÕES PASSARAM!")
        return True


def main():
    """Executa todas as migrations"""
    print("\n" + "="*70)
    print("🚀 MIGRATION COMPLETA - SISTEMA MOTOCHEFE")
    print("="*70)
    print("\n⚠️  IMPORTANTE:")
    print("   - Certifique-se de ter BACKUP do banco")
    print("   - Execute em ambiente LOCAL primeiro")
    print("   - Revise os logs após execução")
    print("\n" + "="*70)

    resposta = input("\n▶️  Deseja continuar? (s/n): ")
    if resposta.lower() != 's':
        print("\n❌ Operação cancelada pelo usuário")
        return

    app = create_app()
    with app.app_context():
        try:
            # Executar migrations em ordem
            migration_crossdocking()
            migration_precificacao_equipes()
            migration_frete_embarque()

            # Verificação final
            if verificacao_final():
                print("\n✅ MIGRATION COMPLETA EXECUTADA COM SUCESSO!")
                print("\n📝 PRÓXIMOS PASSOS:")
                print("   1. Configure as equipes com permitir_prazo e permitir_parcelamento")
                print("   2. Cadastre os CrossDockings se necessário")
                print("   3. Configure preços por equipe em tabela_preco_equipe")
                print("   4. Vincule clientes aos vendedores (cliente_moto.vendedor_id)")
            else:
                print("\n⚠️  MIGRATION CONCLUÍDA COM AVISOS - Revise os erros acima")

        except Exception as e:
            print(f"\n❌ ERRO FATAL: {str(e)}")
            db.session.rollback()
            sys.exit(1)


if __name__ == '__main__':
    main()
