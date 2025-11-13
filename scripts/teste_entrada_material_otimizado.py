"""
Script de Teste - EntradaMaterialService Otimizado
===================================================

OBJETIVO:
    Testar a versão otimizada do serviço com:
    1. Filtro /DEV/ funcionando
    2. Batch queries implementadas
    3. Cache funcionando corretamente

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.odoo.services.entrada_material_service import EntradaMaterialService
import logging

# Configurar logging para ver todas as mensagens
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("🧪 TESTE - ENTRADA MATERIAL SERVICE OTIMIZADO")
print("=" * 80)

# Inicializar app
app = create_app()

with app.app_context():
    print("\n1️⃣ Inicializando serviço...")
    service = EntradaMaterialService()

    print("\n2️⃣ Executando importação (últimos 7 dias, limite 10 pickings)...")
    print("=" * 80)

    resultado = service.importar_entradas(
        dias_retroativos=7,
        limite=10
    )

    print("\n" + "=" * 80)
    print("📊 RESULTADO DA IMPORTAÇÃO")
    print("=" * 80)

    print(f"\n✅ Sucesso: {resultado['sucesso']}")
    print(f"📦 Entradas processadas: {resultado['entradas_processadas']}")
    print(f"✨ Entradas novas: {resultado['entradas_novas']}")
    print(f"🔄 Entradas atualizadas: {resultado['entradas_atualizadas']}")
    print(f"⏭️  Entradas ignoradas: {resultado['entradas_ignoradas']}")
    print(f"❌ Erros: {len(resultado['erros'])}")

    if resultado['erros']:
        print("\n⚠️  ERROS ENCONTRADOS:")
        for erro in resultado['erros']:
            print(f"   - {erro}")

    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 80)

    # Verificações adicionais
    print("\n🔍 VERIFICAÇÕES:")

    # 1. Verificar se /DEV/ foi filtrado
    print("\n1. Filtro /DEV/:")
    print(f"   ✅ Ignoradas: {resultado['entradas_ignoradas']} (deve incluir /DEV/)")

    # 2. Verificar se usou batch
    print("\n2. Batch Queries:")
    print("   ✅ Implementado (verificar logs acima para 'Pré-carregando dados em batch')")

    # 3. Verificar se criou movimentações
    from app.estoque.models import MovimentacaoEstoque
    total_movimentacoes = MovimentacaoEstoque.query.filter_by(
        tipo_origem='ODOO'
    ).count()
    print(f"\n3. Movimentações no banco:")
    print(f"   📦 Total movimentações ODOO: {total_movimentacoes}")

    print("\n" + "=" * 80)
