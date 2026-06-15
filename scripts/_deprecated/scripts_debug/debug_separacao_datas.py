"""
Script para verificar quais campos de DATA estão preenchidos na Separacao
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("="*80)
    print("DEBUG: Campos de Data em Separacao")
    print("="*80)

    # Buscar amostra de separações
    print("\n[ANÁLISE] Verificando campos de data nas separações...")

    separacoes = db.session.query(Separacao).filter(
        Separacao.sincronizado_nf == False
    ).limit(10).all()

    if not separacoes:
        print("   ⚠️ NENHUMA separação com sincronizado_nf=False encontrada!")
        sys.exit(0)

    print(f"\n   ✅ Analisando {len(separacoes)} separações:\n")

    for i, sep in enumerate(separacoes, 1):
        print(f"   Separação {i}:")
        print(f"      - ID: {sep.id}")
        print(f"      - Lote: {sep.separacao_lote_id}")
        print(f"      - Pedido: {sep.num_pedido}")
        print(f"      - Produto: {sep.cod_produto}")
        print(f"      - Status: {sep.status}")
        print(f"      - Qtd: {sep.qtd_saldo}")
        print(f"      - expedicao: {sep.expedicao}")  # ← CAMPO QUE ESTAMOS USANDO
        print(f"      - agendamento: {sep.agendamento}")
        print(f"      - criado_em: {sep.criado_em}")
        print(f"      - data_pedido: {sep.data_pedido}")
        print("")

    # Estatísticas
    print("\n[ESTATÍSTICAS] Campos de data preenchidos:")

    total = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False
    ).scalar()

    com_expedicao = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False,
        Separacao.expedicao.isnot(None)
    ).scalar()

    com_agendamento = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False,
        Separacao.agendamento.isnot(None)
    ).scalar()

    com_data_pedido = db.session.query(func.count(Separacao.id)).filter(
        Separacao.sincronizado_nf == False,
        Separacao.data_pedido.isnot(None)
    ).scalar()

    print(f"\n   Total de separações (sincronizado_nf=False): {total}")
    print(f"   Com 'expedicao' preenchida: {com_expedicao} ({com_expedicao/total*100 if total > 0 else 0:.1f}%)")
    print(f"   Com 'agendamento' preenchida: {com_agendamento} ({com_agendamento/total*100 if total > 0 else 0:.1f}%)")
    print(f"   Com 'data_pedido' preenchida: {com_data_pedido} ({com_data_pedido/total*100 if total > 0 else 0:.1f}%)")

    print("\n" + "="*80)
    print("✅ ANÁLISE CONCLUÍDA!")
    print("="*80)
