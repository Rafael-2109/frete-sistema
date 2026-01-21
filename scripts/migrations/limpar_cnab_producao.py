#!/usr/bin/env python3
"""
Script para limpar dados de CNAB em produção.

Este script remove TODOS os lotes CNAB e seus itens vinculados,
além de resetar os status dos extratos e títulos relacionados.

USO:
    # Simular (não executa nada):
    python scripts/migrations/limpar_cnab_producao.py --dry-run

    # Executar de verdade:
    python scripts/migrations/limpar_cnab_producao.py --execute

IMPORTANTE:
    - Execute primeiro com --dry-run para ver o que será afetado
    - Faça backup antes de executar em produção
    - Este script NÃO reverte ações no Odoo (payments, reconciliações)

Autor: Sistema de Fretes
Data: 2026-01-21
"""

import sys
import os
import argparse
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def inventariar_dados():
    """Faz inventário dos dados que serão afetados."""

    print("\n" + "="*60)
    print("INVENTÁRIO DOS DADOS CNAB")
    print("="*60)

    # 1. Lotes CNAB
    lotes = db.session.execute(text("""
        SELECT id, nome_arquivo, status, hash_arquivo, created_at
        FROM cnab_retorno_lote
        ORDER BY id
    """)).fetchall()

    print(f"\n📁 LOTES CNAB: {len(lotes)}")
    for lote in lotes:
        print(f"   Lote {lote.id}: {lote.nome_arquivo} - {lote.status}")

    # 2. Itens CNAB
    itens = db.session.execute(text("""
        SELECT
            cri.lote_id,
            COUNT(*) as total,
            COUNT(cri.conta_a_receber_id) as com_titulo,
            COUNT(cri.extrato_item_id) as com_extrato,
            SUM(CASE WHEN cri.processado THEN 1 ELSE 0 END) as processados
        FROM cnab_retorno_item cri
        GROUP BY cri.lote_id
        ORDER BY cri.lote_id
    """)).fetchall()

    print(f"\n📋 ITENS CNAB POR LOTE:")
    for item in itens:
        print(f"   Lote {item.lote_id}: {item.total} itens | "
              f"{item.com_titulo} c/ título | {item.com_extrato} c/ extrato | "
              f"{item.processados} processados")

    # 3. Títulos afetados
    titulos = db.session.execute(text("""
        SELECT
            car.id, car.titulo_nf, car.parcela, car.parcela_paga,
            car.status_pagamento_odoo, cri.id as cnab_id
        FROM contas_a_receber car
        JOIN cnab_retorno_item cri ON cri.conta_a_receber_id = car.id
        WHERE car.parcela_paga = TRUE
        ORDER BY car.id
    """)).fetchall()

    print(f"\n💰 TÍTULOS PAGOS VIA CNAB: {len(titulos)}")
    for t in titulos[:10]:  # Mostrar apenas 10 primeiros
        print(f"   ID {t.id}: NF {t.titulo_nf}/{t.parcela} - {t.status_pagamento_odoo}")
    if len(titulos) > 10:
        print(f"   ... e mais {len(titulos) - 10} títulos")

    # 4. Extratos afetados
    extratos = db.session.execute(text("""
        SELECT
            ei.id, ei.status, ei.status_match, ei.valor,
            cri.id as cnab_id, cri.nf_extraida
        FROM extrato_item ei
        JOIN cnab_retorno_item cri ON cri.extrato_item_id = ei.id
        ORDER BY ei.id
    """)).fetchall()

    print(f"\n🏦 EXTRATOS VINCULADOS A CNAB: {len(extratos)}")
    for e in extratos[:10]:
        print(f"   ID {e.id}: R$ {e.valor:.2f} - {e.status} - NF {e.nf_extraida}")
    if len(extratos) > 10:
        print(f"   ... e mais {len(extratos) - 10} extratos")

    # IDs para resetar
    titulo_ids = [t.id for t in titulos]
    extrato_ids = [e.id for e in extratos]
    lote_ids = [l.id for l in lotes]

    return {
        'lotes': lote_ids,
        'titulos': titulo_ids,
        'extratos': extrato_ids,
        'total_itens': sum(i.total for i in itens) if itens else 0
    }


def executar_limpeza(dados, dry_run=True):
    """Executa a limpeza dos dados CNAB."""

    modo = "SIMULAÇÃO" if dry_run else "EXECUÇÃO"
    print(f"\n" + "="*60)
    print(f"🧹 {modo} DA LIMPEZA")
    print("="*60)

    try:
        # 1. Resetar títulos (parcela_paga = False)
        if dados['titulos']:
            titulo_ids_str = ','.join(map(str, dados['titulos']))
            sql_titulos = f"""
                UPDATE contas_a_receber
                SET
                    parcela_paga = FALSE,
                    status_pagamento_odoo = NULL
                WHERE id IN ({titulo_ids_str})
            """
            print(f"\n1️⃣ Resetar {len(dados['titulos'])} títulos:")
            print(f"   SQL: {sql_titulos[:100]}...")

            if not dry_run:
                db.session.execute(text(sql_titulos))
                print(f"   ✅ {len(dados['titulos'])} títulos resetados")
        else:
            print("\n1️⃣ Nenhum título para resetar")

        # 2. Resetar extratos
        if dados['extratos']:
            extrato_ids_str = ','.join(map(str, dados['extratos']))
            sql_extratos = f"""
                UPDATE extrato_item
                SET
                    status = 'PENDENTE',
                    status_match = 'PENDENTE',
                    titulo_receber_id = NULL,
                    titulo_nf = NULL,
                    titulo_parcela = NULL,
                    titulo_valor = NULL,
                    titulo_cliente = NULL,
                    titulo_cnpj = NULL,
                    match_score = NULL,
                    match_criterio = NULL,
                    aprovado = FALSE,
                    aprovado_por = NULL,
                    aprovado_em = NULL,
                    processado_em = NULL,
                    mensagem = NULL,
                    full_reconcile_id = NULL,
                    payment_id = NULL,
                    partial_reconcile_id = NULL
                WHERE id IN ({extrato_ids_str})
            """
            print(f"\n2️⃣ Resetar {len(dados['extratos'])} extratos:")
            print(f"   SQL: UPDATE extrato_item SET status='PENDENTE'... WHERE id IN (...)")

            if not dry_run:
                db.session.execute(text(sql_extratos))
                print(f"   ✅ {len(dados['extratos'])} extratos resetados")
        else:
            print("\n2️⃣ Nenhum extrato para resetar")

        # 3. Excluir itens CNAB
        if dados['lotes']:
            lote_ids_str = ','.join(map(str, dados['lotes']))
            sql_itens = f"""
                DELETE FROM cnab_retorno_item
                WHERE lote_id IN ({lote_ids_str})
            """
            print(f"\n3️⃣ Excluir {dados['total_itens']} itens CNAB:")
            print(f"   SQL: DELETE FROM cnab_retorno_item WHERE lote_id IN ({lote_ids_str})")

            if not dry_run:
                db.session.execute(text(sql_itens))
                print(f"   ✅ Itens CNAB excluídos")
        else:
            print("\n3️⃣ Nenhum item CNAB para excluir")

        # 4. Excluir lotes CNAB
        if dados['lotes']:
            sql_lotes = f"""
                DELETE FROM cnab_retorno_lote
                WHERE id IN ({lote_ids_str})
            """
            print(f"\n4️⃣ Excluir {len(dados['lotes'])} lotes CNAB:")
            print(f"   SQL: DELETE FROM cnab_retorno_lote WHERE id IN ({lote_ids_str})")

            if not dry_run:
                db.session.execute(text(sql_lotes))
                print(f"   ✅ Lotes CNAB excluídos")
        else:
            print("\n4️⃣ Nenhum lote CNAB para excluir")

        # Commit
        if not dry_run:
            db.session.commit()
            print(f"\n✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
        else:
            print(f"\n⚠️ MODO SIMULAÇÃO - Nenhuma alteração foi feita")
            print(f"   Execute com --execute para aplicar as mudanças")

        return True

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERRO: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Limpa dados de CNAB do sistema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
    # Simular (ver o que será afetado):
    python scripts/migrations/limpar_cnab_producao.py --dry-run

    # Executar de verdade:
    python scripts/migrations/limpar_cnab_producao.py --execute

⚠️  ATENÇÃO:
    - Este script NÃO reverte payments/reconciliações no Odoo
    - Para limpar dados no Odoo, use os scripts de auditoria
    - Faça backup antes de executar em produção
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true',
                       help='Simula a limpeza sem executar')
    group.add_argument('--execute', action='store_true',
                       help='Executa a limpeza de verdade')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("LIMPEZA DE DADOS CNAB")
        print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        # Inventariar
        dados = inventariar_dados()

        if not dados['lotes']:
            print("\n✅ Não há lotes CNAB para limpar!")
            return

        # Confirmar se for execução real
        if args.execute:
            print("\n" + "⚠️"*30)
            print("ATENÇÃO: Você está prestes a EXCLUIR dados!")
            print("⚠️"*30)
            resp = input("\nDigite 'SIM' para confirmar: ")
            if resp != 'SIM':
                print("Operação cancelada.")
                return

        # Executar
        executar_limpeza(dados, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
