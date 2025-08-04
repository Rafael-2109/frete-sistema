#!/usr/bin/env python3
"""
Script para inicializar o cache de saldo de estoque
Executar após criar as tabelas com a migração
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inicializar_cache():
    """Inicializa o cache de saldo de estoque"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 60)
            print("INICIALIZAÇÃO DO CACHE DE SALDO DE ESTOQUE")
            print("=" * 60)
            
            # 1. Inicializar cache de saldo
            print("\n1. Criando cache de saldo de estoque...")
            sucesso = SaldoEstoqueCache.inicializar_cache_completo()
            
            if not sucesso:
                print("❌ Erro ao inicializar cache de saldo")
                return False
            
            # 2. Contar registros criados
            total_cache = SaldoEstoqueCache.query.count()
            print(f"✅ {total_cache} produtos no cache de saldo")
            
            # 3. Atualizar projeções para produtos críticos
            print("\n2. Calculando projeções para produtos críticos...")
            produtos_criticos = SaldoEstoqueCache.query.filter(
                SaldoEstoqueCache.status_ruptura.in_(['CRÍTICO', 'ATENÇÃO'])
            ).limit(50).all()  # Limitar para teste inicial
            
            for i, produto in enumerate(produtos_criticos, 1):
                ProjecaoEstoqueCache.atualizar_projecao(produto.cod_produto)
                if i % 10 == 0:
                    print(f"  Processadas {i}/{len(produtos_criticos)} projeções...")
            
            print(f"✅ Projeções calculadas para {len(produtos_criticos)} produtos críticos")
            
            # 4. Estatísticas finais
            print("\n3. Estatísticas do cache:")
            criticos = SaldoEstoqueCache.query.filter_by(status_ruptura='CRÍTICO').count()
            atencao = SaldoEstoqueCache.query.filter_by(status_ruptura='ATENÇÃO').count()
            ok = SaldoEstoqueCache.query.filter_by(status_ruptura='OK').count()
            
            print(f"  - Produtos CRÍTICOS: {criticos}")
            print(f"  - Produtos ATENÇÃO: {atencao}")
            print(f"  - Produtos OK: {ok}")
            
            print("\n" + "=" * 60)
            print("✅ CACHE INICIALIZADO COM SUCESSO!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO FATAL: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    sucesso = inicializar_cache()
    sys.exit(0 if sucesso else 1)