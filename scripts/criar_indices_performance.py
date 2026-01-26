#!/usr/bin/env python3
"""
Script para criar índices de performance faltantes no banco de dados.

Executa em duas formas:
1. Python local: python scripts/criar_indices_performance.py
2. SQL no Render Shell: copiar os comandos SQL gerados

18 índices identificados via análise de .claude/ralph-loop/IMPLEMENTATION_PLAN.md
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text, inspect

# Lista de índices a criar (tabela, nome_indice, colunas)
INDICES_ALTA_PRIORIDADE = [
    # Separacao - já tem idx_sep_num_pedido e idx_sep_cotacao
    ('separacao', 'idx_sep_rota_sub_rota', ['rota', 'sub_rota']),

    # Embarques
    ('embarques', 'idx_embarque_transportadora', ['transportadora_id']),
    ('embarques', 'idx_embarque_status', ['status']),
    ('embarques', 'idx_embarque_cotacao', ['cotacao_id']),

    # Embarque Itens
    ('embarque_itens', 'idx_embarque_item_embarque', ['embarque_id']),
    ('embarque_itens', 'idx_embarque_item_status', ['status']),
    ('embarque_itens', 'idx_embarque_item_cotacao', ['cotacao_id']),

    # Fretes
    ('fretes', 'idx_frete_embarque', ['embarque_id']),
    ('fretes', 'idx_frete_transportadora', ['transportadora_id']),
    ('fretes', 'idx_frete_status', ['status']),
]

INDICES_MEDIA_PRIORIDADE = [
    # Embarque Itens
    ('embarque_itens', 'idx_embarque_item_cnpj', ['cnpj_cliente']),
    ('embarque_itens', 'idx_embarque_item_pedido', ['pedido']),

    # Fretes
    ('fretes', 'idx_frete_fatura', ['fatura_frete_id']),

    # Faturas Frete
    ('faturas_frete', 'idx_fatura_transportadora', ['transportadora_id']),
    ('faturas_frete', 'idx_fatura_status', ['status_conferencia']),

    # Conta Corrente Transportadora (nota: tabela real é conta_corrente_transportadoras)
    ('conta_corrente_transportadoras', 'idx_cc_transportadora', ['transportadora_id']),
    ('conta_corrente_transportadoras', 'idx_cc_frete', ['frete_id']),

    # Carteira Principal
    ('carteira_principal', 'idx_carteira_cond_pgto', ['cond_pgto_pedido']),
    ('carteira_principal', 'idx_carteira_data_entrega', ['data_entrega_pedido']),
]


def verificar_indice_existe(inspector, tabela, indice_nome):
    """Verifica se um índice já existe na tabela"""
    try:
        indices = inspector.get_indexes(tabela)
        return any(idx['name'] == indice_nome for idx in indices)
    except Exception:
        return False


def criar_indice(tabela, nome, colunas):
    """Cria um índice se não existir"""
    colunas_str = ', '.join(colunas)
    sql = f'CREATE INDEX IF NOT EXISTS {nome} ON {tabela} ({colunas_str})'
    return sql


def main():
    print("=" * 60)
    print("CRIAÇÃO DE ÍNDICES DE PERFORMANCE")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Gerar SQLs
        sqls_alta = []
        sqls_media = []

        print("\n📊 ALTA PRIORIDADE:")
        for tabela, nome, colunas in INDICES_ALTA_PRIORIDADE:
            existe = verificar_indice_existe(inspector, tabela, nome)
            status = "✅ Já existe" if existe else "❌ Faltando"
            print(f"  {nome} em {tabela}: {status}")
            if not existe:
                sqls_alta.append(criar_indice(tabela, nome, colunas))

        print("\n📊 MÉDIA PRIORIDADE:")
        for tabela, nome, colunas in INDICES_MEDIA_PRIORIDADE:
            existe = verificar_indice_existe(inspector, tabela, nome)
            status = "✅ Já existe" if existe else "❌ Faltando"
            print(f"  {nome} em {tabela}: {status}")
            if not existe:
                sqls_media.append(criar_indice(tabela, nome, colunas))

        # Executar criação
        total_criados = 0

        if sqls_alta:
            print(f"\n⚡ Criando {len(sqls_alta)} índices de ALTA prioridade...")
            for sql in sqls_alta:
                try:
                    db.session.execute(text(sql))
                    print(f"  ✅ {sql[:60]}...")
                    total_criados += 1
                except Exception as e:
                    print(f"  ❌ Erro: {e}")
            db.session.commit()

        if sqls_media:
            print(f"\n📦 Criando {len(sqls_media)} índices de MÉDIA prioridade...")
            for sql in sqls_media:
                try:
                    db.session.execute(text(sql))
                    print(f"  ✅ {sql[:60]}...")
                    total_criados += 1
                except Exception as e:
                    print(f"  ❌ Erro: {e}")
            db.session.commit()

        print("\n" + "=" * 60)
        print(f"✅ CONCLUÍDO: {total_criados} índices criados")
        print("=" * 60)

        # Gerar SQL para Render Shell
        if sqls_alta or sqls_media:
            print("\n📋 SQL PARA RENDER SHELL:")
            print("-" * 40)
            for sql in sqls_alta + sqls_media:
                print(f"{sql};")


if __name__ == '__main__':
    main()
