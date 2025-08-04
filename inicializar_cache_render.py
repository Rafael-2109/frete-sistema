#!/usr/bin/env python3
"""
Script para inicializar o cache de estoque no Render
Este script pode ser executado manualmente ou pelo build do Render
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inicializar_cache_render():
    """Inicializa o cache de saldo de estoque para produção"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 60)
            print("INICIALIZAÇÃO DO CACHE DE ESTOQUE - RENDER")
            print("=" * 60)
            
            # Verificar se já existe cache
            cache_existente = SaldoEstoqueCache.query.count()
            
            if cache_existente > 0:
                print(f"ℹ️  Já existem {cache_existente} produtos no cache")
                
                # Em produção, apenas atualizar se não houver cache
                resposta = input("Deseja RECRIAR todo o cache? (s/N): ").strip().lower()
                if resposta != 's':
                    print("✅ Mantendo cache existente")
                    return True
            
            # Inicializar cache
            print("\n1. Criando cache de saldo de estoque...")
            print("   📦 Considerando códigos unificados")
            print("   🔄 Isso pode demorar alguns minutos...")
            
            sucesso = SaldoEstoqueCache.inicializar_cache_completo()
            
            if not sucesso:
                print("❌ Erro ao inicializar cache de saldo")
                return False
            
            # Contar registros criados
            total_cache = SaldoEstoqueCache.query.count()
            print(f"✅ {total_cache} produtos no cache de saldo")
            
            # Em produção, calcular projeções apenas para produtos muito críticos
            print("\n2. Calculando projeções para produtos críticos...")
            produtos_criticos = SaldoEstoqueCache.query.filter(
                SaldoEstoqueCache.saldo_atual < 0  # Apenas estoque negativo
            ).limit(20).all()  # Limitar para não demorar muito
            
            for i, produto in enumerate(produtos_criticos, 1):
                ProjecaoEstoqueCache.atualizar_projecao(produto.cod_produto)
                if i % 5 == 0:
                    print(f"   Processadas {i}/{len(produtos_criticos)} projeções...")
            
            print(f"✅ Projeções calculadas para {len(produtos_criticos)} produtos críticos")
            
            # Estatísticas finais
            print("\n3. Estatísticas do cache:")
            criticos = SaldoEstoqueCache.query.filter_by(status_ruptura='CRÍTICO').count()
            atencao = SaldoEstoqueCache.query.filter_by(status_ruptura='ATENÇÃO').count()
            ok = SaldoEstoqueCache.query.filter_by(status_ruptura='OK').count()
            
            print(f"  - Produtos CRÍTICOS: {criticos}")
            print(f"  - Produtos ATENÇÃO: {atencao}")
            print(f"  - Produtos OK: {ok}")
            
            print("\n" + "=" * 60)
            print("✅ CACHE INICIALIZADO COM SUCESSO NO RENDER!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO FATAL: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Detectar se está no Render
    if os.getenv('RENDER'):
        print("🚀 Executando no Render...")
        # No Render, não pedir confirmação
        import sys
        original_input = input
        sys.modules['builtins'].input = lambda _: 'n'  # Default para não recriar
    
    sucesso = inicializar_cache_render()
    sys.exit(0 if sucesso else 1)