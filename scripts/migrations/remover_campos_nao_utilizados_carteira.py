"""
Script para remover campos não utilizados da tabela carteira_principal.

Campos removidos: 48 campos que nunca foram preenchidos (100% NULL ou vazio)
- Dados operacionais: data_entrega, hora_agendamento, agendamento_confirmado
- Análise de estoque: menor_estoque_produto_d7, saldo_estoque_pedido, saldo_estoque_pedido_forcado
- Dados de carga/lote: qtd_saldo, valor_saldo, pallet, peso
- Dados de rota: rota, sub_rota
- Totalizadores cliente: valor_saldo_total, pallet_total, peso_total, valor_cliente_pedido, pallet_cliente_pedido, peso_cliente_pedido
- Totalizadores produto: qtd_total_produto_carteira, estoque
- Projeção D0-D28: estoque_d0 até estoque_d28 (28 campos)

Roda: python scripts/migrations/remover_campos_nao_utilizados_carteira.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def remover_campos():
    """Remove campos não utilizados da carteira_principal."""

    campos_remover = [
        # Dados operacionais (todos vazios ou com strings vazias '')
        'expedicao',
        'agendamento',
        'protocolo',
        'roteirizacao',
        'data_entrega',
        'hora_agendamento',
        'agendamento_confirmado',

        # Vínculo separação (não utilizado aqui - está em Separacao)
        'separacao_lote_id',

        # Análise de estoque
        'menor_estoque_produto_d7',
        'saldo_estoque_pedido',
        'saldo_estoque_pedido_forcado',

        # Dados de carga/lote
        'qtd_saldo',
        'valor_saldo',
        'pallet',
        'peso',

        # Dados de rota
        'rota',
        'sub_rota',

        # Totalizadores cliente
        'valor_saldo_total',
        'pallet_total',
        'peso_total',
        'valor_cliente_pedido',
        'pallet_cliente_pedido',
        'peso_cliente_pedido',

        # Totalizadores produto
        'qtd_total_produto_carteira',
        'estoque',

        # Projeção D0-D28
        'estoque_d0', 'estoque_d1', 'estoque_d2', 'estoque_d3', 'estoque_d4',
        'estoque_d5', 'estoque_d6', 'estoque_d7', 'estoque_d8', 'estoque_d9',
        'estoque_d10', 'estoque_d11', 'estoque_d12', 'estoque_d13', 'estoque_d14',
        'estoque_d15', 'estoque_d16', 'estoque_d17', 'estoque_d18', 'estoque_d19',
        'estoque_d20', 'estoque_d21', 'estoque_d22', 'estoque_d23', 'estoque_d24',
        'estoque_d25', 'estoque_d26', 'estoque_d27', 'estoque_d28',
    ]

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("REMOVENDO CAMPOS NÃO UTILIZADOS DA CARTEIRA_PRINCIPAL")
        print("=" * 60)
        print()

        # Verifica quais campos existem antes
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'carteira_principal'
        """))
        colunas_existentes = {row[0] for row in result}

        print(f"Total de colunas antes: {len(colunas_existentes)}")
        print()

        removidos = 0
        ignorados = 0

        for campo in campos_remover:
            if campo in colunas_existentes:
                try:
                    db.session.execute(text(f"ALTER TABLE carteira_principal DROP COLUMN IF EXISTS {campo}"))
                    print(f"  ✅ Removido: {campo}")
                    removidos += 1
                except Exception as e:
                    print(f"  ❌ Erro ao remover {campo}: {e}")
            else:
                print(f"  ⏭️  Ignorado (não existe): {campo}")
                ignorados += 1

        db.session.commit()

        # Verifica colunas restantes
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'carteira_principal'
            ORDER BY ordinal_position
        """))
        colunas_restantes = [row[0] for row in result]

        print()
        print("=" * 60)
        print(f"RESULTADO:")
        print(f"  Campos removidos: {removidos}")
        print(f"  Campos ignorados: {ignorados}")
        print(f"  Colunas restantes: {len(colunas_restantes)}")
        print("=" * 60)
        print()
        print("Colunas restantes:")
        for col in colunas_restantes:
            print(f"  - {col}")


if __name__ == '__main__':
    remover_campos()
