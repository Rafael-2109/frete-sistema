#!/usr/bin/env python3
"""
Teste direto das funções do BI sem passar pela API
"""
from app import create_app, db
from app.bi.models import BiFreteAgregado, BiDespesaDetalhada
from datetime import date, timedelta
from sqlalchemy import func, distinct

app = create_app()

with app.app_context():
    print("=== TESTE DIRETO DO MÓDULO BI ===\n")

    # Teste 1: Verificar se há dados nas tabelas
    print("1. CONTAGEM DE REGISTROS:")
    print(f"   - BiFreteAgregado: {BiFreteAgregado.query.count()}")
    print(f"   - BiDespesaDetalhada: {BiDespesaDetalhada.query.count()}")

    # Teste 2: Buscar indicadores principais (simulando a API)
    print("\n2. INDICADORES PRINCIPAIS:")
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)

    dados_mes = db.session.query(
        func.sum(BiFreteAgregado.valor_pago_total).label('custo_total'),
        func.sum(BiFreteAgregado.valor_despesas_extras).label('despesas_total'),
        func.sum(BiFreteAgregado.peso_total_kg).label('peso_total'),
        func.sum(BiFreteAgregado.valor_total_nf).label('valor_faturado'),
        func.count(distinct(BiFreteAgregado.transportadora_id)).label('qtd_transportadoras'),
        func.avg(BiFreteAgregado.custo_por_kg).label('custo_medio_kg')
    ).filter(
        BiFreteAgregado.data_referencia >= inicio_mes
    ).first()

    if dados_mes:
        print(f"   - Custo Total: R$ {float(dados_mes.custo_total or 0):,.2f}")
        print(f"   - Despesas: R$ {float(dados_mes.despesas_total or 0):,.2f}")
        print(f"   - Peso Total: {float(dados_mes.peso_total or 0):,.0f} kg")
        print(f"   - Valor Faturado: R$ {float(dados_mes.valor_faturado or 0):,.2f}")
        print(f"   - Transportadoras: {int(dados_mes.qtd_transportadoras or 0)}")
        print(f"   - Custo Médio/kg: R$ {float(dados_mes.custo_medio_kg or 0):.2f}")
    else:
        print("   ❌ Nenhum dado encontrado")

    # Teste 3: Buscar dados por transportadora
    print("\n3. TOP 3 TRANSPORTADORAS:")
    top_transp = db.session.query(
        BiFreteAgregado.transportadora_nome,
        func.sum(BiFreteAgregado.valor_pago_total).label('total')
    ).filter(
        BiFreteAgregado.data_referencia >= inicio_mes
    ).group_by(
        BiFreteAgregado.transportadora_nome
    ).order_by(
        func.sum(BiFreteAgregado.valor_pago_total).desc()
    ).limit(3).all()

    for idx, t in enumerate(top_transp, 1):
        print(f"   {idx}. {t.transportadora_nome}: R$ {float(t.total or 0):,.2f}")

    print("\n=== TESTE CONCLUÍDO ===")