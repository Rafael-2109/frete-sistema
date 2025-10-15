#!/usr/bin/env python3
"""
Script de Verificação - Carga Inicial MotoChefe
Data: 14/10/2025

OBJETIVO:
Verificar se todas as tabelas necessárias para a carga inicial existem

EXECUÇÃO LOCAL:
python3 migrations/carga_inicial_motochefe_local.py
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import inspect


def verificar_tabelas_necessarias():
    """Verifica se todas as tabelas necessárias existem"""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        tabelas_existentes = set(inspector.get_table_names())

        # Tabelas necessárias para Fase 1, 2 e 3
        tabelas_necessarias = {
            # Fase 1
            'equipe_vendas_moto',
            'transportadora_moto',
            'empresa_venda_moto',
            'cross_docking',
            'custos_operacionais',
            'tabela_preco_equipe',
            'tabela_preco_crossdocking',

            # Fase 2
            'vendedor_moto',
            'modelo_moto',

            # Fase 3
            'cliente_moto',
            'moto',
        }

        print("\n" + "=" * 70)
        print("VERIFICAÇÃO DE TABELAS PARA CARGA INICIAL - MOTOCHEFE")
        print("=" * 70)

        faltando = []

        for tabela in sorted(tabelas_necessarias):
            existe = tabela in tabelas_existentes
            status = "✅" if existe else "❌"
            print(f"{status} {tabela}")

            if not existe:
                faltando.append(tabela)

        print("=" * 70)

        if faltando:
            print(f"\n❌ FALTAM {len(faltando)} TABELAS!")
            print("\n⚠️  Execute o script de criação de tabelas:")
            print("   python3 app/motochefe/scripts/criar_tabelas_localmente.py")
            return False
        else:
            print(f"\n✅ TODAS AS {len(tabelas_necessarias)} TABELAS EXISTEM!")
            print("\n🚀 Sistema pronto para carga inicial!")
            print("\n📋 Próximos passos:")
            print("   1. Acesse: http://localhost:5000/motochefe/carga-inicial")
            print("   2. Baixe os templates Excel")
            print("   3. Preencha com seus dados")
            print("   4. Importe seguindo a ordem das fases")
            return True


def verificar_campos_criticos():
    """Verifica se campos críticos adicionados por migrations existem"""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)

        print("\n" + "=" * 70)
        print("VERIFICAÇÃO DE CAMPOS CRÍTICOS (MIGRATIONS)")
        print("=" * 70)

        campos_verificar = [
            ('cliente_moto', 'vendedor_id'),
            ('cliente_moto', 'crossdocking'),
            ('equipe_vendas_moto', 'permitir_prazo'),
            ('equipe_vendas_moto', 'permitir_parcelamento'),
            ('equipe_vendas_moto', 'custo_movimentacao'),
            ('equipe_vendas_moto', 'tipo_precificacao'),
            ('moto', 'empresa_pagadora_id'),
            ('moto', 'status_pagamento_custo'),
        ]

        faltando = []

        for tabela, campo in campos_verificar:
            # Verificar se tabela existe
            if tabela not in inspector.get_table_names():
                print(f"⚠️  {tabela}.{campo} - Tabela não existe")
                continue

            # Verificar se campo existe
            colunas = [col['name'] for col in inspector.get_columns(tabela)]
            existe = campo in colunas

            status = "✅" if existe else "❌"
            print(f"{status} {tabela}.{campo}")

            if not existe:
                faltando.append(f"{tabela}.{campo}")

        print("=" * 70)

        if faltando:
            print(f"\n⚠️  FALTAM {len(faltando)} CAMPOS!")
            print("\n⚠️  Execute as migrations faltantes:")
            print("   python3 app/motochefe/scripts/criar_tabelas_localmente.py")
            return False
        else:
            print(f"\n✅ TODOS OS CAMPOS CRÍTICOS EXISTEM!")
            return True


def main():
    """Função principal"""
    print("\n" + "=" * 70)
    print("🔍 VERIFICAÇÃO DO SISTEMA - CARGA INICIAL MOTOCHEFE")
    print("=" * 70)

    # 1. Verificar tabelas
    tabelas_ok = verificar_tabelas_necessarias()

    # 2. Verificar campos críticos
    campos_ok = verificar_campos_criticos()

    # Resultado final
    print("\n" + "=" * 70)
    if tabelas_ok and campos_ok:
        print("✅ SISTEMA PRONTO PARA CARGA INICIAL!")
        print("=" * 70)
        print("\n📖 Consulte a documentação:")
        print("   DOCUMENTACAO_CARGA_INICIAL_MOTOCHEFE.md")
        return 0
    else:
        print("❌ SISTEMA NÃO ESTÁ PRONTO")
        print("=" * 70)
        print("\n🔧 Execute as correções indicadas acima")
        return 1


if __name__ == '__main__':
    sys.exit(main())
