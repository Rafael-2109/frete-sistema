#!/usr/bin/env python3
"""
Script para processar CNABs que ficaram pendentes (status AGUARDANDO).

Estes são CNABs que têm título E extrato vinculados, mas não foram
processados (baixa automática não foi executada).

USO:
    # Listar CNABs pendentes:
    python scripts/migrations/processar_cnabs_pendentes.py --listar

    # Processar CNABs pendentes:
    python scripts/migrations/processar_cnabs_pendentes.py --processar

Autor: Sistema de Fretes
Data: 2026-01-21
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.financeiro.models import CnabRetornoItem, ExtratoItem, ContasAReceber


def listar_pendentes():
    """Lista CNABs que estão pendentes (AGUARDANDO)."""

    # CNABs com título E extrato vinculados mas não processados
    pendentes = db.session.query(
        CnabRetornoItem
    ).filter(
        CnabRetornoItem.processado == False,
        CnabRetornoItem.status_match == 'MATCH_ENCONTRADO',
        CnabRetornoItem.conta_a_receber_id.isnot(None),
        CnabRetornoItem.extrato_item_id.isnot(None)
    ).all()

    print("\n" + "="*70)
    print("CNABs PENDENTES (AGUARDANDO)")
    print("="*70)

    if not pendentes:
        print("✅ Nenhum CNAB pendente encontrado!")
        return []

    print(f"Encontrados {len(pendentes)} CNABs pendentes:\n")

    for cnab in pendentes:
        titulo = db.session.get(ContasAReceber, cnab.conta_a_receber_id)
        extrato = db.session.get(ExtratoItem, cnab.extrato_item_id)

        titulo_pago = titulo.parcela_paga if titulo else None
        extrato_status = extrato.status if extrato else None

        print(f"CNAB {cnab.id}: NF {cnab.nf_extraida}/{cnab.parcela_extraida}")
        print(f"  Título ID: {cnab.conta_a_receber_id} | Pago: {titulo_pago}")
        print(f"  Extrato ID: {cnab.extrato_item_id} | Status: {extrato_status}")
        print(f"  Erro anterior: {cnab.erro_mensagem or '-'}")
        print()

    return pendentes


def processar_pendentes():
    """Processa CNABs pendentes (executa baixa automática)."""
    from app.financeiro.services.cnab400_processor_service import Cnab400ProcessorService

    pendentes = listar_pendentes()

    if not pendentes:
        return

    print("\n" + "="*70)
    print("PROCESSANDO CNABs PENDENTES")
    print("="*70)

    processor = Cnab400ProcessorService()
    sucesso = 0
    erro = 0

    for cnab in pendentes:
        try:
            print(f"\n📋 Processando CNAB {cnab.id} (NF {cnab.nf_extraida}/{cnab.parcela_extraida})...")

            # Executar baixa automática
            resultado = processor._executar_baixa_automatica(cnab, 'SCRIPT_MANUAL')

            if resultado:
                sucesso += 1
                print(f"   ✅ Baixa automática executada com sucesso!")
            else:
                erro += 1
                print(f"   ⚠️ Baixa retornou False. Erro: {cnab.erro_mensagem}")

        except Exception as e:
            erro += 1
            print(f"   ❌ Erro: {e}")
            cnab.erro_mensagem = f"Erro processamento manual: {str(e)}"

    db.session.commit()

    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    print(f"✅ Sucesso: {sucesso}")
    print(f"❌ Erros: {erro}")


def main():
    parser = argparse.ArgumentParser(
        description='Processa CNABs pendentes (status AGUARDANDO)'
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--listar', action='store_true',
                       help='Lista CNABs pendentes sem processar')
    group.add_argument('--processar', action='store_true',
                       help='Processa CNABs pendentes (executa baixa)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.listar:
            listar_pendentes()
        elif args.processar:
            processar_pendentes()


if __name__ == '__main__':
    main()
