#!/usr/bin/env python3
"""
Script para testar a sincronização de faturamento
"""

import sys
import os
sys.path.insert(0, '.')
os.environ['FLASK_ENV'] = 'development'

from app import create_app, db
from app.odoo.services.faturamento_service import FaturamentoService
from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 60)
print("TESTE DE SINCRONIZAÇÃO DE FATURAMENTO")
print("=" * 60)

# Criar app e contexto
app = create_app()
with app.app_context():
    print("\n1. Testando FaturamentoService diretamente...")
    print("-" * 40)
    
    try:
        faturamento_service = FaturamentoService()
        
        # Tentar obter dados do Odoo primeiro
        print("📊 Buscando dados do Odoo...")
        resultado_odoo = faturamento_service.obter_faturamento_otimizado(
            usar_filtro_postado=True,
            limite=10  # Apenas 10 registros para teste
        )
        
        if resultado_odoo.get('sucesso'):
            print(f"✅ Dados obtidos do Odoo: {len(resultado_odoo.get('dados', []))} registros")
            
            # Se tem dados, mostrar primeiro registro
            if resultado_odoo.get('dados'):
                primeiro = resultado_odoo['dados'][0]
                print(f"   Exemplo: NF {primeiro.get('numero_nf')} - {primeiro.get('nome_cliente')}")
        else:
            print(f"❌ Erro ao buscar dados: {resultado_odoo.get('erro')}")
            
    except Exception as e:
        print(f"❌ Erro no FaturamentoService: {e}")
    
    print("\n2. Testando Sincronização Integrada...")
    print("-" * 40)
    
    try:
        sync_service = SincronizacaoIntegradaService()
        
        # Verificar se o faturamento está sendo chamado
        print("🔄 Executando sincronização integrada (apenas faturamento)...")
        
        # Executar apenas a parte do faturamento
        resultado_fat = sync_service._sincronizar_faturamento_seguro()
        
        if resultado_fat.get('sucesso'):
            print(f"✅ Faturamento sincronizado:")
            print(f"   - Registros importados: {resultado_fat.get('registros_importados', 0)}")
            print(f"   - Novos: {resultado_fat.get('registros_novos', 0)}")
            print(f"   - Atualizados: {resultado_fat.get('registros_atualizados', 0)}")
            print(f"   - Movimentações estoque: {resultado_fat.get('movimentacoes_criadas', 0)}")
        else:
            print(f"❌ Erro na sincronização: {resultado_fat.get('erro')}")
            
    except Exception as e:
        print(f"❌ Erro na sincronização integrada: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Verificando dados no banco...")
    print("-" * 40)
    
    try:
        from app.faturamento.models import FaturamentoProduto
        
        # Contar registros no banco
        total_faturamento = db.session.query(FaturamentoProduto).count()
        print(f"📊 Total de registros de faturamento no banco: {total_faturamento}")
        
        # Últimos 5 registros
        ultimos = db.session.query(FaturamentoProduto).order_by(
            FaturamentoProduto.created_at.desc()
        ).limit(5).all()
        
        if ultimos:
            print("📋 Últimos 5 registros:")
            for nf in ultimos:
                print(f"   - NF {nf.numero_nf} - {nf.nome_cliente} - {nf.created_at}")
        
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)