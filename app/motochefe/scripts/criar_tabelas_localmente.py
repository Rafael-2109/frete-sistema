"""
Criar/Atualizar Tabelas Localmente - Sistema MotoChefe
Data: 08/01/2025

OBJETIVO: Criar TODAS as tabelas do sistema MotoChefe no banco LOCAL

FUNCIONA EM:
- Banco vazio (cria tudo do zero)
- Banco parcialmente populado (adiciona apenas o que falta)

INCLUI:
- Todas as tabelas base do sistema
- Campos adicionados por migrations (CrossDocking, Parcelamento, Precificação)
- Campo empresa_pagadora_id em embarque_moto

INSTRUÇÕES:
1. Certifique-se de ter backup do banco
2. Execute: python3 app/motochefe/scripts/criar_tabelas_localmente.py
3. Verifique os logs para confirmar sucesso
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import inspect, text


def verificar_tabela_existe(nome_tabela):
    """Verifica se tabela existe no banco"""
    inspector = inspect(db.engine)
    return nome_tabela in inspector.get_table_names()


def verificar_coluna_existe(nome_tabela, nome_coluna):
    """Verifica se coluna existe em uma tabela"""
    if not verificar_tabela_existe(nome_tabela):
        return False

    inspector = inspect(db.engine)
    colunas = [col['name'] for col in inspector.get_columns(nome_tabela)]
    return nome_coluna in colunas


def criar_todas_tabelas():
    """Cria TODAS as tabelas usando SQLAlchemy models"""
    print("\n" + "="*70)
    print("📦 CRIANDO TABELAS BASE (SQLAlchemy)")
    print("="*70)

    try:
        # Importar TODOS os modelos para registrá-los no metadata
        from app.motochefe.models import (
            # Cadastros
            EquipeVendasMoto, VendedorMoto, TransportadoraMoto, ClienteMoto,
            EmpresaVendaMoto, FornecedorMontagem,

            # Produtos
            ModeloMoto, Moto,

            # Financeiro
            TituloFinanceiro, ComissaoVendedor, MovimentacaoFinanceira, TituloAPagar,

            # Vendas
            PedidoVendaMoto, PedidoVendaMotoItem,

            # Logística
            EmbarqueMoto, EmbarquePedido,

            # Operacional
            CustosOperacionais, DespesaMensal
        )

        print("\n🔄 Criando tabelas via db.create_all()...")
        db.create_all()
        print("✅ Tabelas base criadas com sucesso!")

        return True

    except ImportError as e:
        print(f"⚠️  Aviso ao importar modelos: {str(e)}")
        print("   Algumas tabelas podem não existir ainda (normal se são novas)")

        # Mesmo com erro de import, tenta criar as tabelas conhecidas
        try:
            db.create_all()
            print("✅ Tabelas base criadas (com avisos)")
            return True
        except Exception as e2:
            print(f"❌ Erro ao criar tabelas: {str(e2)}")
            return False

    except Exception as e:
        print(f"❌ Erro fatal ao criar tabelas: {str(e)}")
        return False


def criar_tabelas_extras():
    """Cria tabelas que podem não estar nos models (CrossDocking, etc)"""
    print("\n" + "="*70)
    print("📦 CRIANDO TABELAS EXTRAS")
    print("="*70)

    tabelas = [
        {
            'nome': 'cross_docking',
            'sql': """
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
        },
        {
            'nome': 'tabela_preco_crossdocking',
            'sql': """
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

                    CONSTRAINT uk_crossdocking_modelo_preco UNIQUE (crossdocking_id, modelo_id)
                );

                CREATE INDEX IF NOT EXISTS idx_tabela_preco_cd_crossdocking
                ON tabela_preco_crossdocking(crossdocking_id);

                CREATE INDEX IF NOT EXISTS idx_tabela_preco_cd_modelo
                ON tabela_preco_crossdocking(modelo_id);
            """
        },
        {
            'nome': 'tabela_preco_equipe',
            'sql': """
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

                    CONSTRAINT uk_equipe_modelo_preco UNIQUE (equipe_vendas_id, modelo_id)
                );

                CREATE INDEX IF NOT EXISTS idx_tabela_preco_equipe_equipe
                ON tabela_preco_equipe(equipe_vendas_id);

                CREATE INDEX IF NOT EXISTS idx_tabela_preco_equipe_modelo
                ON tabela_preco_equipe(modelo_id);
            """
        }
    ]

    criadas = 0
    ja_existiam = 0

    for tabela_info in tabelas:
        nome = tabela_info['nome']

        if verificar_tabela_existe(nome):
            print(f"✓  Tabela {nome} - JÁ EXISTE")
            ja_existiam += 1
        else:
            try:
                print(f"🔄 Tabela {nome} - Criando...")
                db.session.execute(text(tabela_info['sql']))
                db.session.commit()
                print(f"✅ Tabela {nome} - CRIADA")
                criadas += 1
            except Exception as e:
                print(f"❌ Tabela {nome} - ERRO: {str(e)}")
                db.session.rollback()

    print(f"\n📊 Resumo: {criadas} criadas, {ja_existiam} já existiam")


def adicionar_campos_faltantes():
    """Adiciona campos que podem estar faltando (migrations)"""
    print("\n" + "="*70)
    print("🔧 ADICIONANDO CAMPOS FALTANTES")
    print("="*70)

    campos_adicionar = [
        # ClienteMoto
        {
            'tabela': 'cliente_moto',
            'campo': 'vendedor_id',
            'sql': """
                ALTER TABLE cliente_moto
                ADD COLUMN IF NOT EXISTS vendedor_id INTEGER REFERENCES vendedor_moto(id);
                CREATE INDEX IF NOT EXISTS idx_cliente_moto_vendedor ON cliente_moto(vendedor_id);
            """,
            'descricao': 'ClienteMoto.vendedor_id'
        },
        {
            'tabela': 'cliente_moto',
            'campo': 'crossdocking',
            'sql': """
                ALTER TABLE cliente_moto
                ADD COLUMN IF NOT EXISTS crossdocking BOOLEAN DEFAULT FALSE NOT NULL;
            """,
            'descricao': 'ClienteMoto.crossdocking'
        },
        {
            'tabela': 'cliente_moto',
            'campo': 'crossdocking_id',
            'sql': """
                ALTER TABLE cliente_moto
                ADD COLUMN IF NOT EXISTS crossdocking_id INTEGER REFERENCES cross_docking(id);
                CREATE INDEX IF NOT EXISTS idx_cliente_moto_crossdocking ON cliente_moto(crossdocking_id);
            """,
            'descricao': 'ClienteMoto.crossdocking_id'
        },

        # EquipeVendasMoto
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'permitir_prazo',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS permitir_prazo BOOLEAN DEFAULT FALSE NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.permitir_prazo'
        },
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'permitir_parcelamento',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS permitir_parcelamento BOOLEAN DEFAULT FALSE NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.permitir_parcelamento'
        },
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'custo_movimentacao',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS custo_movimentacao NUMERIC(15, 2) DEFAULT 0 NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.custo_movimentacao'
        },
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'incluir_custo_movimentacao',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS incluir_custo_movimentacao BOOLEAN DEFAULT FALSE NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.incluir_custo_movimentacao'
        },
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'tipo_precificacao',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS tipo_precificacao VARCHAR(20) DEFAULT 'TABELA' NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.tipo_precificacao'
        },
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'markup',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS markup NUMERIC(15, 2) DEFAULT 0 NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.markup'
        },
        {
            'tabela': 'equipe_vendas_moto',
            'campo': 'permitir_montagem',
            'sql': """
                ALTER TABLE equipe_vendas_moto
                ADD COLUMN IF NOT EXISTS permitir_montagem BOOLEAN DEFAULT TRUE NOT NULL;
            """,
            'descricao': 'EquipeVendasMoto.permitir_montagem'
        },

        # PedidoVendaMoto
        {
            'tabela': 'pedido_venda_moto',
            'campo': 'prazo_dias',
            'sql': """
                ALTER TABLE pedido_venda_moto
                ADD COLUMN IF NOT EXISTS prazo_dias INTEGER DEFAULT 0 NOT NULL;
            """,
            'descricao': 'PedidoVendaMoto.prazo_dias'
        },
        {
            'tabela': 'pedido_venda_moto',
            'campo': 'numero_parcelas',
            'sql': """
                ALTER TABLE pedido_venda_moto
                ADD COLUMN IF NOT EXISTS numero_parcelas INTEGER DEFAULT 1 NOT NULL;
            """,
            'descricao': 'PedidoVendaMoto.numero_parcelas'
        },

        # EmbarqueMoto
        {
            'tabela': 'embarque_moto',
            'campo': 'empresa_pagadora_id',
            'sql': """
                ALTER TABLE embarque_moto
                ADD COLUMN IF NOT EXISTS empresa_pagadora_id INTEGER;

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

                CREATE INDEX IF NOT EXISTS ix_embarque_moto_empresa_pagadora_id
                ON embarque_moto(empresa_pagadora_id);
            """,
            'descricao': 'EmbarqueMoto.empresa_pagadora_id'
        },
    ]

    adicionados = 0
    ja_existiam = 0
    erros = []

    for campo_info in campos_adicionar:
        tabela = campo_info['tabela']
        campo = campo_info['campo']
        descricao = campo_info['descricao']

        # Verificar se tabela existe
        if not verificar_tabela_existe(tabela):
            print(f"⚠️  {descricao} - Tabela {tabela} não existe (será criada depois)")
            continue

        # Verificar se campo já existe
        if verificar_coluna_existe(tabela, campo):
            print(f"✓  {descricao} - JÁ EXISTE")
            ja_existiam += 1
            continue

        # Adicionar campo
        try:
            print(f"🔄 {descricao} - Adicionando...")
            db.session.execute(text(campo_info['sql']))
            db.session.commit()
            print(f"✅ {descricao} - ADICIONADO")
            adicionados += 1
        except Exception as e:
            print(f"❌ {descricao} - ERRO: {str(e)}")
            db.session.rollback()
            erros.append(descricao)

    print(f"\n📊 Resumo: {adicionados} adicionados, {ja_existiam} já existiam, {len(erros)} erros")

    if erros:
        print("\n⚠️  Campos com erro:")
        for erro in erros:
            print(f"   - {erro}")


def verificacao_final():
    """Verificação final do banco"""
    print("\n" + "="*70)
    print("🔍 VERIFICAÇÃO FINAL")
    print("="*70)

    inspector = inspect(db.engine)
    tabelas = inspector.get_table_names()

    print(f"\n📊 Total de tabelas no banco: {len(tabelas)}")

    # Tabelas essenciais
    tabelas_essenciais = [
        'equipe_vendas_moto',
        'vendedor_moto',
        'cliente_moto',
        'modelo_moto',
        'moto',
        'pedido_venda_moto',
        'pedido_venda_moto_item',
        'titulo_financeiro',
        'movimentacao_financeira',
        'embarque_moto',
        'cross_docking',
        'tabela_preco_equipe'
    ]

    print("\n✅ Tabelas essenciais:")
    faltando = []
    for tabela in tabelas_essenciais:
        if tabela in tabelas:
            print(f"   ✓ {tabela}")
        else:
            print(f"   ✗ {tabela} - FALTANDO")
            faltando.append(tabela)

    # Campos críticos adicionados por migration
    print("\n✅ Campos críticos (migrations):")
    campos_verificar = [
        ('cliente_moto', 'vendedor_id'),
        ('cliente_moto', 'crossdocking'),
        ('equipe_vendas_moto', 'permitir_prazo'),
        ('equipe_vendas_moto', 'permitir_parcelamento'),
        ('equipe_vendas_moto', 'custo_movimentacao'),
        ('equipe_vendas_moto', 'tipo_precificacao'),
        ('pedido_venda_moto', 'prazo_dias'),
        ('embarque_moto', 'empresa_pagadora_id'),
    ]

    campos_faltando = []
    for tabela, campo in campos_verificar:
        if verificar_coluna_existe(tabela, campo):
            print(f"   ✓ {tabela}.{campo}")
        else:
            print(f"   ✗ {tabela}.{campo} - FALTANDO")
            campos_faltando.append(f"{tabela}.{campo}")

    if faltando or campos_faltando:
        print("\n⚠️  ATENÇÃO: Itens faltando detectados!")
        return False
    else:
        print("\n✅ TUDO OK - Banco local sincronizado!")
        return True


def main():
    """Executa criação completa do banco local"""
    print("\n" + "="*70)
    print("🚀 CRIAR/ATUALIZAR BANCO LOCAL - MOTOCHEFE")
    print("="*70)
    print("\n⚠️  IMPORTANTE:")
    print("   - Este script CRIA tabelas e ADICIONA campos")
    print("   - Funciona em banco vazio ou parcialmente populado")
    print("   - Use em ambiente LOCAL primeiro")
    print("\n" + "="*70)

    resposta = input("\n▶️  Deseja continuar? (s/n): ")
    if resposta.lower() != 's':
        print("\n❌ Operação cancelada pelo usuário")
        return

    app = create_app()
    with app.app_context():
        try:
            # 1. Criar tabelas base via SQLAlchemy
            print("\n🔄 FASE 1: Criando tabelas base...")
            if not criar_todas_tabelas():
                print("\n⚠️  Erro ao criar tabelas base, mas continuando...")

            # 2. Criar tabelas extras (CrossDocking, etc)
            print("\n🔄 FASE 2: Criando tabelas extras...")
            criar_tabelas_extras()

            # 3. Adicionar campos faltantes
            print("\n🔄 FASE 3: Adicionando campos faltantes...")
            adicionar_campos_faltantes()

            # 4. Verificação final
            print("\n🔄 FASE 4: Verificação final...")
            sucesso = verificacao_final()

            print("\n" + "="*70)
            if sucesso:
                print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
            else:
                print("⚠️  PROCESSO CONCLUÍDO COM AVISOS")
            print("="*70)

            print("\n📝 PRÓXIMOS PASSOS:")
            print("   1. Revise os logs acima para verificar erros")
            print("   2. Execute os testes do sistema")
            print("   3. Configure dados iniciais (equipes, vendedores, etc)")

        except Exception as e:
            print(f"\n❌ ERRO FATAL: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)


if __name__ == '__main__':
    main()
