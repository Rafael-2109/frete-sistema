#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migração: Sistema de Dupla Conferência - Abatimentos + Odoo

Este script cria:
1. Tabela mapeamento_tipo_odoo (mapeia tipos sistema -> tipos Odoo)
2. Novos campos em contas_a_receber_abatimento (vinculação com Odoo)
3. Novos campos em contas_a_receber_reconciliacao (classificação)
4. Novos tipos de abatimento (DESCONTO ST, CONTRATO, AJUSTE FINANCEIRO)
5. Dados iniciais de mapeamento

Para executar localmente:
    python scripts/migracao_abatimentos_odoo.py

Data: 2025-11-28
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime


def verificar_coluna_existe(tabela: str, coluna: str) -> bool:
    """Verifica se uma coluna já existe na tabela"""
    result = db.session.execute(text(f"""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = '{tabela}' AND column_name = '{coluna}'
    """))
    return result.scalar() > 0


def verificar_tabela_existe(tabela: str) -> bool:
    """Verifica se uma tabela já existe"""
    result = db.session.execute(text(f"""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = '{tabela}'
    """))
    return result.scalar() > 0


def criar_tabela_mapeamento():
    """Cria a tabela mapeamento_tipo_odoo"""
    print("\n" + "=" * 60)
    print("1. CRIANDO TABELA mapeamento_tipo_odoo")
    print("=" * 60)

    if verificar_tabela_existe('mapeamento_tipo_odoo'):
        print("   ✅ Tabela já existe, pulando...")
        return

    sql = """
    CREATE TABLE mapeamento_tipo_odoo (
        id SERIAL PRIMARY KEY,
        tipo_sistema_id INTEGER NOT NULL REFERENCES contas_a_receber_tipos(id),
        tipo_odoo VARCHAR(50) NOT NULL,
        prioridade INTEGER DEFAULT 100,
        tolerancia_valor FLOAT DEFAULT 0.02,
        ativo BOOLEAN DEFAULT TRUE NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por VARCHAR(100),
        CONSTRAINT uq_mapeamento_tipo_sistema_odoo UNIQUE (tipo_sistema_id, tipo_odoo)
    );

    CREATE INDEX idx_mapeamento_tipo_odoo ON mapeamento_tipo_odoo(tipo_odoo);
    CREATE INDEX idx_mapeamento_tipo_sistema ON mapeamento_tipo_odoo(tipo_sistema_id);
    """

    db.session.execute(text(sql))
    db.session.commit()
    print("   ✅ Tabela criada com sucesso!")


def adicionar_campos_abatimento():
    """Adiciona novos campos em contas_a_receber_abatimento"""
    print("\n" + "=" * 60)
    print("2. ADICIONANDO CAMPOS EM contas_a_receber_abatimento")
    print("=" * 60)

    campos = [
        ("reconciliacao_odoo_id", "INTEGER REFERENCES contas_a_receber_reconciliacao(id)"),
        ("status_vinculacao", "VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL"),
        ("ultima_tentativa_vinculacao", "TIMESTAMP"),
    ]

    for campo, tipo in campos:
        if verificar_coluna_existe('contas_a_receber_abatimento', campo):
            print(f"   ✅ Coluna {campo} já existe, pulando...")
        else:
            sql = f"ALTER TABLE contas_a_receber_abatimento ADD COLUMN {campo} {tipo}"
            db.session.execute(text(sql))
            print(f"   ✅ Coluna {campo} adicionada!")

    # Criar índices
    try:
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_abatimento_status_vinculacao
            ON contas_a_receber_abatimento(status_vinculacao)
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_abatimento_reconciliacao
            ON contas_a_receber_abatimento(reconciliacao_odoo_id)
        """))
        print("   ✅ Índices criados!")
    except Exception as e:
        print(f"   ⚠️ Índices já existem ou erro: {e}")

    db.session.commit()


def adicionar_campos_reconciliacao():
    """Adiciona novos campos em contas_a_receber_reconciliacao"""
    print("\n" + "=" * 60)
    print("3. ADICIONANDO CAMPOS EM contas_a_receber_reconciliacao")
    print("=" * 60)

    campos = [
        ("journal_code", "VARCHAR(20)"),
        ("payment_odoo_id", "INTEGER"),
    ]

    for campo, tipo in campos:
        if verificar_coluna_existe('contas_a_receber_reconciliacao', campo):
            print(f"   ✅ Coluna {campo} já existe, pulando...")
        else:
            sql = f"ALTER TABLE contas_a_receber_reconciliacao ADD COLUMN {campo} {tipo}"
            db.session.execute(text(sql))
            print(f"   ✅ Coluna {campo} adicionada!")

    # Criar índice para tipo_baixa se não existir
    try:
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reconciliacao_tipo_baixa
            ON contas_a_receber_reconciliacao(tipo_baixa)
        """))
        print("   ✅ Índice tipo_baixa criado!")
    except Exception as e:
        print(f"   ⚠️ Índice já existe ou erro: {e}")

    db.session.commit()


def criar_novos_tipos_abatimento():
    """Cria novos tipos de abatimento no sistema"""
    print("\n" + "=" * 60)
    print("4. CRIANDO NOVOS TIPOS DE ABATIMENTO")
    print("=" * 60)

    from app.financeiro.models import ContasAReceberTipo

    novos_tipos = [
        {
            'tipo': 'DESCONTO ST',
            'tabela': 'contas_a_receber_abatimento',
            'campo': 'tipo',
            'considera_a_receber': True,
            'explicacao': 'Abatimento referente a Substituição Tributária'
        },
        {
            'tipo': 'CONTRATO',
            'tabela': 'contas_a_receber_abatimento',
            'campo': 'tipo',
            'considera_a_receber': True,
            'explicacao': 'Desconto por acordo/contrato comercial'
        },
        {
            'tipo': 'AJUSTE FINANCEIRO',
            'tabela': 'contas_a_receber_abatimento',
            'campo': 'tipo',
            'considera_a_receber': True,
            'explicacao': 'Ajuste financeiro (juros, multa, outros)'
        },
    ]

    for tipo_data in novos_tipos:
        # Verificar se já existe
        existe = ContasAReceberTipo.query.filter_by(
            tipo=tipo_data['tipo'],
            tabela=tipo_data['tabela'],
            campo=tipo_data['campo']
        ).first()

        if existe:
            print(f"   ✅ Tipo '{tipo_data['tipo']}' já existe, pulando...")
        else:
            novo_tipo = ContasAReceberTipo(
                tipo=tipo_data['tipo'],
                tabela=tipo_data['tabela'],
                campo=tipo_data['campo'],
                considera_a_receber=tipo_data['considera_a_receber'],
                explicacao=tipo_data['explicacao'],
                ativo=True,
                criado_por='Sistema - Migração'
            )
            db.session.add(novo_tipo)
            print(f"   ✅ Tipo '{tipo_data['tipo']}' criado!")

    db.session.commit()


def criar_mapeamentos_iniciais():
    """Cria mapeamentos iniciais entre tipos do sistema e tipos do Odoo"""
    print("\n" + "=" * 60)
    print("5. CRIANDO MAPEAMENTOS SISTEMA -> ODOO")
    print("=" * 60)

    from app.financeiro.models import ContasAReceberTipo, MapeamentoTipoOdoo

    # Mapeamentos: tipo_sistema -> tipo_odoo
    mapeamentos = [
        # VERBA -> abatimento_acordo
        ('VERBA', 'abatimento_acordo', 10),
        # ACAO COMERCIAL -> abatimento_acordo
        ('ACAO COMERCIAL', 'abatimento_acordo', 20),
        # DEVOLUCAO -> devolucao
        ('DEVOLUCAO', 'devolucao', 10),
        # DESCONTO ST -> abatimento_st
        ('DESCONTO ST', 'abatimento_st', 10),
        # CONTRATO -> abatimento_acordo
        ('CONTRATO', 'abatimento_acordo', 30),
        # AJUSTE FINANCEIRO -> abatimento_outros
        ('AJUSTE FINANCEIRO', 'abatimento_outros', 10),
    ]

    for tipo_sistema_nome, tipo_odoo, prioridade in mapeamentos:
        # Buscar tipo do sistema
        tipo_sistema = ContasAReceberTipo.query.filter_by(
            tipo=tipo_sistema_nome,
            tabela='contas_a_receber_abatimento',
            campo='tipo'
        ).first()

        if not tipo_sistema:
            print(f"   ⚠️ Tipo '{tipo_sistema_nome}' não encontrado, pulando...")
            continue

        # Verificar se mapeamento já existe
        existe = MapeamentoTipoOdoo.query.filter_by(
            tipo_sistema_id=tipo_sistema.id,
            tipo_odoo=tipo_odoo
        ).first()

        if existe:
            print(f"   ✅ Mapeamento '{tipo_sistema_nome}' -> '{tipo_odoo}' já existe, pulando...")
        else:
            novo_mapeamento = MapeamentoTipoOdoo(
                tipo_sistema_id=tipo_sistema.id,
                tipo_odoo=tipo_odoo,
                prioridade=prioridade,
                tolerancia_valor=0.02,
                ativo=True,
                criado_por='Sistema - Migração'
            )
            db.session.add(novo_mapeamento)
            print(f"   ✅ Mapeamento '{tipo_sistema_nome}' -> '{tipo_odoo}' criado!")

    db.session.commit()


def verificar_migracao():
    """Verifica se a migração foi bem sucedida"""
    print("\n" + "=" * 60)
    print("6. VERIFICANDO MIGRAÇÃO")
    print("=" * 60)

    # Verificar tabela mapeamento_tipo_odoo
    result = db.session.execute(text("""
        SELECT COUNT(*) FROM mapeamento_tipo_odoo
    """))
    qtd_mapeamentos = result.scalar()
    print(f"   📊 Mapeamentos criados: {qtd_mapeamentos}")

    # Verificar novos tipos
    result = db.session.execute(text("""
        SELECT COUNT(*) FROM contas_a_receber_tipos
        WHERE tipo IN ('DESCONTO ST', 'CONTRATO', 'AJUSTE FINANCEIRO')
    """))
    qtd_novos_tipos = result.scalar()
    print(f"   📊 Novos tipos criados: {qtd_novos_tipos}")

    # Verificar colunas em abatimento
    for col in ['reconciliacao_odoo_id', 'status_vinculacao', 'ultima_tentativa_vinculacao']:
        existe = verificar_coluna_existe('contas_a_receber_abatimento', col)
        status = "✅" if existe else "❌"
        print(f"   {status} Coluna abatimento.{col}: {'existe' if existe else 'NÃO existe'}")

    # Verificar colunas em reconciliacao
    for col in ['journal_code', 'payment_odoo_id']:
        existe = verificar_coluna_existe('contas_a_receber_reconciliacao', col)
        status = "✅" if existe else "❌"
        print(f"   {status} Coluna reconciliacao.{col}: {'existe' if existe else 'NÃO existe'}")


def main():
    """Executa a migração completa"""
    print("\n" + "=" * 60)
    print("MIGRAÇÃO: Sistema de Dupla Conferência - Abatimentos + Odoo")
    print("Data:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    app = create_app()

    with app.app_context():
        try:
            # 1. Criar tabela de mapeamento
            criar_tabela_mapeamento()

            # 2. Adicionar campos em abatimento
            adicionar_campos_abatimento()

            # 3. Adicionar campos em reconciliacao
            adicionar_campos_reconciliacao()

            # 4. Criar novos tipos de abatimento
            criar_novos_tipos_abatimento()

            # 5. Criar mapeamentos iniciais
            criar_mapeamentos_iniciais()

            # 6. Verificar migração
            verificar_migracao()

            print("\n" + "=" * 60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO NA MIGRAÇÃO: {e}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
