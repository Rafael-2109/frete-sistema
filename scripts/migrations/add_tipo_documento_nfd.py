"""
Migration: Adicionar campos tipo_documento, status_odoo, status_monitoramento em nf_devolucao

Objetivo:
- Diferenciar NFD (Nota Fiscal de Devolução) de NF (NF de Venda revertida)
- Rastrear status no Odoo e no Monitoramento
- Permitir vinculação com NF de venda original e Nota de Crédito do Odoo

Novos campos:
- tipo_documento: 'NFD' ou 'NF'
- status_odoo: 'Devolução', 'Revertida', 'Cancelada'
- status_monitoramento: 'Cancelada', 'Devolvida', 'Troca de NF'
- odoo_nf_venda_id: ID da NF de venda original no Odoo
- odoo_nota_credito_id: ID da Nota de Crédito no Odoo

Executar: python scripts/migrations/add_tipo_documento_nfd.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(nome_tabela: str, nome_coluna: str) -> bool:
    """Verifica se uma coluna já existe na tabela"""
    resultado = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': nome_tabela, 'coluna': nome_coluna})
    return resultado.scalar()


def adicionar_campo_tipo_documento():
    """Adiciona o campo tipo_documento"""
    if verificar_coluna_existe('nf_devolucao', 'tipo_documento'):
        print("✓ Campo tipo_documento já existe")
        return False

    print("Adicionando campo tipo_documento...")
    db.session.execute(text("""
        ALTER TABLE nf_devolucao
        ADD COLUMN tipo_documento VARCHAR(10) DEFAULT 'NFD' NOT NULL
    """))
    print("✓ Campo tipo_documento adicionado")
    return True


def adicionar_campo_status_odoo():
    """Adiciona o campo status_odoo"""
    if verificar_coluna_existe('nf_devolucao', 'status_odoo'):
        print("✓ Campo status_odoo já existe")
        return False

    print("Adicionando campo status_odoo...")
    db.session.execute(text("""
        ALTER TABLE nf_devolucao
        ADD COLUMN status_odoo VARCHAR(30)
    """))
    print("✓ Campo status_odoo adicionado")
    return True


def adicionar_campo_status_monitoramento():
    """Adiciona o campo status_monitoramento"""
    if verificar_coluna_existe('nf_devolucao', 'status_monitoramento'):
        print("✓ Campo status_monitoramento já existe")
        return False

    print("Adicionando campo status_monitoramento...")
    db.session.execute(text("""
        ALTER TABLE nf_devolucao
        ADD COLUMN status_monitoramento VARCHAR(30)
    """))
    print("✓ Campo status_monitoramento adicionado")
    return True


def adicionar_campo_odoo_nf_venda_id():
    """Adiciona o campo odoo_nf_venda_id"""
    if verificar_coluna_existe('nf_devolucao', 'odoo_nf_venda_id'):
        print("✓ Campo odoo_nf_venda_id já existe")
        return False

    print("Adicionando campo odoo_nf_venda_id...")
    db.session.execute(text("""
        ALTER TABLE nf_devolucao
        ADD COLUMN odoo_nf_venda_id INTEGER
    """))
    print("✓ Campo odoo_nf_venda_id adicionado")
    return True


def adicionar_campo_odoo_nota_credito_id():
    """Adiciona o campo odoo_nota_credito_id"""
    if verificar_coluna_existe('nf_devolucao', 'odoo_nota_credito_id'):
        print("✓ Campo odoo_nota_credito_id já existe")
        return False

    print("Adicionando campo odoo_nota_credito_id...")
    db.session.execute(text("""
        ALTER TABLE nf_devolucao
        ADD COLUMN odoo_nota_credito_id INTEGER
    """))
    print("✓ Campo odoo_nota_credito_id adicionado")
    return True


def criar_indices():
    """Cria os índices para os novos campos"""
    indices = [
        ('idx_nfd_tipo_documento', 'tipo_documento'),
        ('idx_nfd_odoo_nf_venda', 'odoo_nf_venda_id'),
        ('idx_nfd_status_odoo_monit', 'status_odoo, status_monitoramento'),
    ]

    for nome_indice, colunas in indices:
        # Verificar se índice já existe
        resultado = db.session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'nf_devolucao' AND indexname = :indice
            )
        """), {'indice': nome_indice})

        if resultado.scalar():
            print(f"✓ Índice {nome_indice} já existe")
        else:
            print(f"Criando índice {nome_indice}...")
            db.session.execute(text(f"""
                CREATE INDEX {nome_indice} ON nf_devolucao ({colunas})
            """))
            print(f"✓ Índice {nome_indice} criado")


def atualizar_registros_existentes():
    """
    Atualiza registros existentes para definir tipo_documento baseado na origem
    e sincroniza status_monitoramento com EntregaMonitorada
    """
    print("\nAtualizando registros existentes...")

    # Definir tipo_documento='NFD' para todos os registros existentes
    resultado = db.session.execute(text("""
        UPDATE nf_devolucao
        SET tipo_documento = 'NFD',
            status_odoo = CASE
                WHEN odoo_dfe_id IS NOT NULL THEN 'Devolução'
                ELSE NULL
            END
        WHERE tipo_documento IS NULL OR tipo_documento = ''
    """))
    print(f"✓ {resultado.rowcount} registros atualizados com tipo_documento='NFD'")

    # Sincronizar status_monitoramento com EntregaMonitorada
    resultado = db.session.execute(text("""
        UPDATE nf_devolucao nfd
        SET status_monitoramento = em.status_finalizacao
        FROM entregas_monitoradas em
        WHERE nfd.entrega_monitorada_id = em.id
          AND em.status_finalizacao IN ('Cancelada', 'Devolvida', 'Troca de NF')
          AND nfd.status_monitoramento IS NULL
    """))
    print(f"✓ {resultado.rowcount} registros sincronizados com status_monitoramento")


def executar_migration():
    """Executa a migration completa"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Adicionar campos tipo_documento e status")
            print("=" * 60)
            print()

            # Adicionar campos
            adicionar_campo_tipo_documento()
            adicionar_campo_status_odoo()
            adicionar_campo_status_monitoramento()
            adicionar_campo_odoo_nf_venda_id()
            adicionar_campo_odoo_nota_credito_id()

            # Criar índices
            print()
            criar_indices()

            # Atualizar registros existentes
            print()
            atualizar_registros_existentes()

            # Commit
            db.session.commit()

            print()
            print("=" * 60)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            raise


if __name__ == '__main__':
    executar_migration()
