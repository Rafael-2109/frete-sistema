#!/usr/bin/env python3
"""
Script de teste para verificar se a unificação de códigos está funcionando
na análise de ruptura para o produto 4759098
"""

import sys
import os
os.environ['PYTHONUNBUFFERED'] = '1'

from datetime import datetime
from app import create_app
from app.estoque.models import UnificacaoCodigos

def test_unificacao_4759098():
    """Testa unificação do produto 4759098"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60, flush=True)
        print("TESTE DE UNIFICAÇÃO - PRODUTO 4759098", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()
        
        # Verificar códigos unificados
        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados('4759098')
        print(f"\n✅ Códigos unificados para 4759098: {codigos_relacionados}")
        
        # Testar função de expansão da API
        from app.carteira.routes.ruptura_api_sem_cache import expandir_codigos_unificados
        
        produtos_teste = ['4759098']
        expandidos = expandir_codigos_unificados(produtos_teste)
        
        print(f"\n📊 Expansão de códigos:")
        for produto, codigos in expandidos.items():
            print(f"   {produto} -> {codigos}")
        
        # Buscar produções de todos os códigos
        from app.producao.models import ProgramacaoProducao
        from sqlalchemy import func
        
        todos_codigos = list(codigos_relacionados)
        
        print(f"\n🏭 Buscando produções para códigos: {todos_codigos}")
        
        producoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto.in_(todos_codigos),
            ProgramacaoProducao.data_programacao >= datetime.now().date()
        ).order_by(
            ProgramacaoProducao.data_programacao
        ).all()
        
        print(f"\n📅 Produções encontradas:")
        for prod in producoes:
            print(f"   - {prod.cod_produto}: {prod.data_programacao} -> {prod.qtd_programada} un")
        
        # Agrupar produções por data (simulando a lógica da API)
        producoes_agrupadas = {}
        for prod in producoes:
            data_str = prod.data_programacao.isoformat()
            if data_str not in producoes_agrupadas:
                producoes_agrupadas[data_str] = {
                    'data': prod.data_programacao,
                    'qtd': 0,
                    'codigos': []
                }
            producoes_agrupadas[data_str]['qtd'] += float(prod.qtd_programada)
            producoes_agrupadas[data_str]['codigos'].append(prod.cod_produto)
        
        print(f"\n✨ Produções AGRUPADAS por data (unificadas):")
        for data, info in sorted(producoes_agrupadas.items()):
            print(f"   - {data}: {info['qtd']} un (códigos: {', '.join(info['codigos'])})")
        
        # Calcular total de produção
        total_producao = sum(info['qtd'] for info in producoes_agrupadas.values())
        print(f"\n🎯 TOTAL DE PRODUÇÃO UNIFICADA: {total_producao} un")
        
        print("\n" + "=" * 60)
        print("✅ TESTE CONCLUÍDO")
        print("=" * 60)

if __name__ == '__main__':
    test_unificacao_4759098()