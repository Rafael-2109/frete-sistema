#!/usr/bin/env python
"""
Script para testar trigger de Separacao
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def testar_trigger_separacao():
    """Testa se trigger da Separacao está funcionando"""
    app = create_app()
    
    with app.app_context():
        try:
            from app.separacao.models import Separacao
            from app.estoque.models_hibrido import EstoqueProjecaoCache, cache_memoria
            from app.estoque.triggers_hibrido import produtos_para_recalcular, processar_recalculos_pendentes
            
            print("\n=== TESTE DE TRIGGER SEPARACAO ===")
            
            # 1. Buscar uma separação existente
            separacao = Separacao.query.filter(
                Separacao.cod_produto.isnot(None)
            ).first()
            
            if not separacao:
                print("❌ Nenhuma separação encontrada para teste")
                return
            
            cod_produto = separacao.cod_produto
            print(f"Testando com produto: {cod_produto}")
            print(f"Separação ID: {separacao.id}, Lote: {separacao.separacao_lote_id}")
            
            # 2. Verificar cache antes
            cache_antes = EstoqueProjecaoCache.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if cache_antes:
                print(f"Cache antes - Atualizado em: {cache_antes.calculado_em}")
                print(f"Cache válido até: {cache_antes.valido_ate}")
            else:
                print("Sem cache antes")
            
            # 3. Limpar produtos pendentes
            produtos_para_recalcular.clear()
            
            # 4. Atualizar data da separação
            data_original = separacao.expedicao
            nova_data = datetime.now().date() + timedelta(days=5)
            
            print(f"\nAlterando data de {data_original} para {nova_data}")
            separacao.expedicao = nova_data
            
            # Forçar flush para disparar trigger
            db.session.flush()
            
            # 5. Verificar se produto foi marcado para recálculo
            print(f"\nProdutos marcados para recálculo: {produtos_para_recalcular}")
            
            if cod_produto in produtos_para_recalcular:
                print("✅ Trigger disparou! Produto marcado para recálculo")
            else:
                print("❌ Trigger NÃO disparou! Produto não foi marcado")
            
            # 6. Verificar se cache foi invalidado
            cache_status = cache_memoria.get(cod_produto)
            if cache_status is None:
                print("✅ Cache em memória foi invalidado")
            else:
                print("❌ Cache em memória ainda existe")
            
            # 7. Processar recálculos pendentes
            print("\nProcessando recálculos pendentes...")
            processar_recalculos_pendentes()
            
            # 8. Verificar cache depois
            cache_depois = EstoqueProjecaoCache.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if cache_depois:
                print(f"\nCache depois - Atualizado em: {cache_depois.calculado_em}")
                if cache_antes and cache_depois.calculado_em > cache_antes.calculado_em:
                    print("✅ CACHE FOI ATUALIZADO!")
                else:
                    print("❌ Cache não foi atualizado")
            
            # 9. Reverter mudança
            separacao.expedicao = data_original
            db.session.commit()
            print("\n✅ Teste concluído, mudanças revertidas")
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    testar_trigger_separacao()