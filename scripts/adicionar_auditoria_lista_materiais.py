"""
Migration: Adicionar campos de auditoria em ListaMateriais e criar ListaMateriaisHistorico

Data: 2025-01-28
Objetivo:
  - Adicionar campos de auditoria expandidos em lista_materiais
  - Criar tabela lista_materiais_historico
  - Adicionar índices para performance

IMPORTANTE: Execute primeiro localmente, depois no Render via SQL
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text, inspect
from datetime import datetime


def verificar_colunas_existentes(tabela, colunas):
    """Verifica quais colunas já existem na tabela"""
    inspector = inspect(db.engine)
    colunas_existentes = [col['name'] for col in inspector.get_columns(tabela)]

    resultado = {}
    for coluna in colunas:
        resultado[coluna] = coluna in colunas_existentes

    return resultado


def adicionar_campos_auditoria():
    """Adiciona campos de auditoria em lista_materiais"""

    print("\n" + "="*70)
    print("📋 ETAPA 1: Adicionar campos de auditoria em lista_materiais")
    print("="*70)

    # Campos a adicionar
    campos_novos = {
        'atualizado_em': 'TIMESTAMP',
        'atualizado_por': 'VARCHAR(100)',
        'inativado_em': 'TIMESTAMP',
        'inativado_por': 'VARCHAR(100)',
        'motivo_inativacao': 'TEXT'
    }

    # Verificar quais já existem
    status = verificar_colunas_existentes('lista_materiais', campos_novos.keys())

    for campo, tipo in campos_novos.items():
        if status[campo]:
            print(f"   ⏭️  Campo '{campo}' já existe - pulando")
        else:
            try:
                sql = f"ALTER TABLE lista_materiais ADD COLUMN {campo} {tipo};"
                db.session.execute(text(sql))
                db.session.commit()
                print(f"   ✅ Campo '{campo}' adicionado com sucesso")
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Erro ao adicionar '{campo}': {e}")
                raise

    # Adicionar default em versao se não tiver
    try:
        sql_default = """
        ALTER TABLE lista_materiais
        ALTER COLUMN versao SET DEFAULT 'v1';
        """
        db.session.execute(text(sql_default))
        db.session.commit()
        print(f"   ✅ Default 'v1' adicionado ao campo 'versao'")
    except Exception as e:
        db.session.rollback()
        print(f"   ⚠️  Aviso ao adicionar default: {e}")

    # Atualizar registros existentes sem versão
    try:
        sql_update = """
        UPDATE lista_materiais
        SET versao = 'v1'
        WHERE versao IS NULL OR versao = '';
        """
        resultado = db.session.execute(text(sql_update))
        db.session.commit()
        print(f"   ✅ {resultado.rowcount} registros atualizados com versão 'v1'")
    except Exception as e:
        db.session.rollback()
        print(f"   ⚠️  Aviso ao atualizar versões: {e}")

    print("\n✅ Campos de auditoria adicionados com sucesso!")


def criar_tabela_historico():
    """Cria tabela lista_materiais_historico"""

    print("\n" + "="*70)
    print("📋 ETAPA 2: Criar tabela lista_materiais_historico")
    print("="*70)

    # Verificar se tabela já existe
    inspector = inspect(db.engine)
    if inspector.has_table('lista_materiais_historico'):
        print("   ⏭️  Tabela 'lista_materiais_historico' já existe - pulando")
        return

    sql_create = """
    CREATE TABLE lista_materiais_historico (
        id SERIAL PRIMARY KEY,
        lista_materiais_id INTEGER NOT NULL,
        operacao VARCHAR(20) NOT NULL,

        -- Snapshot dos dados
        cod_produto_produzido VARCHAR(50) NOT NULL,
        nome_produto_produzido VARCHAR(255),
        cod_produto_componente VARCHAR(50) NOT NULL,
        nome_produto_componente VARCHAR(255),
        versao VARCHAR(100),

        -- Valores ANTES
        qtd_utilizada_antes NUMERIC(15, 6),
        status_antes VARCHAR(10),

        -- Valores DEPOIS
        qtd_utilizada_depois NUMERIC(15, 6),
        status_depois VARCHAR(10),

        -- Metadados
        alterado_em TIMESTAMP NOT NULL DEFAULT NOW(),
        alterado_por VARCHAR(100) NOT NULL,
        motivo TEXT,
        dados_adicionais JSONB
    );
    """

    try:
        db.session.execute(text(sql_create))
        db.session.commit()
        print("   ✅ Tabela 'lista_materiais_historico' criada com sucesso")
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Erro ao criar tabela: {e}")
        raise


def criar_indices():
    """Cria índices para performance"""

    print("\n" + "="*70)
    print("📋 ETAPA 3: Criar índices para performance")
    print("="*70)

    indices = [
        # Índices em lista_materiais
        {
            'nome': 'idx_lista_materiais_status_data',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_lista_materiais_status_data ON lista_materiais(status, criado_em);'
        },

        # Índices em lista_materiais_historico
        {
            'nome': 'idx_historico_lista_materiais_id',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_historico_lista_materiais_id ON lista_materiais_historico(lista_materiais_id);'
        },
        {
            'nome': 'idx_historico_produto_data',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_historico_produto_data ON lista_materiais_historico(cod_produto_produzido, alterado_em);'
        },
        {
            'nome': 'idx_historico_componente_data',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_historico_componente_data ON lista_materiais_historico(cod_produto_componente, alterado_em);'
        },
        {
            'nome': 'idx_historico_operacao_data',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_historico_operacao_data ON lista_materiais_historico(operacao, alterado_em);'
        },
        {
            'nome': 'idx_historico_alterado_por',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_historico_alterado_por ON lista_materiais_historico(alterado_por);'
        }
    ]

    for indice in indices:
        try:
            db.session.execute(text(indice['sql']))
            db.session.commit()
            print(f"   ✅ Índice '{indice['nome']}' criado com sucesso")
        except Exception as e:
            db.session.rollback()
            print(f"   ⚠️  Aviso ao criar '{indice['nome']}': {e}")

    print("\n✅ Índices criados com sucesso!")


def verificar_migracao():
    """Verifica se a migração foi aplicada corretamente"""

    print("\n" + "="*70)
    print("🔍 VERIFICAÇÃO FINAL")
    print("="*70)

    inspector = inspect(db.engine)

    # Verificar tabelas
    tabelas_necessarias = ['lista_materiais', 'lista_materiais_historico']
    for tabela in tabelas_necessarias:
        existe = inspector.has_table(tabela)
        status = "✅" if existe else "❌"
        print(f"   {status} Tabela '{tabela}': {'EXISTE' if existe else 'NÃO ENCONTRADA'}")

    # Verificar colunas em lista_materiais
    if inspector.has_table('lista_materiais'):
        colunas_esperadas = [
            'atualizado_em', 'atualizado_por',
            'inativado_em', 'inativado_por', 'motivo_inativacao'
        ]
        status_colunas = verificar_colunas_existentes('lista_materiais', colunas_esperadas)

        print(f"\n   Campos de auditoria em lista_materiais:")
        for coluna, existe in status_colunas.items():
            status = "✅" if existe else "❌"
            print(f"      {status} {coluna}")

    # Contar registros
    try:
        count_lista = db.session.execute(text("SELECT COUNT(*) FROM lista_materiais;")).scalar()
        print(f"\n   📊 Total de registros em lista_materiais: {count_lista}")

        count_historico = db.session.execute(text("SELECT COUNT(*) FROM lista_materiais_historico;")).scalar()
        print(f"   📊 Total de registros em lista_materiais_historico: {count_historico}")
    except Exception as e:
        print(f"   ⚠️  Erro ao contar registros: {e}")

    print("\n" + "="*70)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)


def main():
    """Executa a migração completa"""

    print("\n" + "="*70)
    print("🚀 INICIANDO MIGRAÇÃO - Auditoria de Lista de Materiais")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    app = create_app()

    with app.app_context():
        try:
            # Etapa 1: Adicionar campos de auditoria
            adicionar_campos_auditoria()

            # Etapa 2: Criar tabela de histórico
            criar_tabela_historico()

            # Etapa 3: Criar índices
            criar_indices()

            # Verificação final
            verificar_migracao()

        except Exception as e:
            print(f"\n❌ ERRO DURANTE MIGRAÇÃO: {e}")
            print("\n🔄 Executando rollback...")
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()
